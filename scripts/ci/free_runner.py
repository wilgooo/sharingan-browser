#!/usr/bin/env python3
"""Disposable PUBLIC GitHub-hosted Linux runner only. Never run on a personal host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_cache import export_packages

ROOT = Path(__file__).resolve().parents[2]
GIB = 1024 ** 3
# These are experiment thresholds, NOT Chromium's official capacity requirement.
MIN_START_GIB = 70
MIN_BUILD_GIB = 15
RESERVE_GIB = 3
# Fixed allowlist. Never derive deletion targets from user input/environment.
RECLAIM_PATHS = (
    '/usr/share/dotnet', '/usr/local/lib/android', '/opt/ghc',
    '/usr/local/.ghcup', '/usr/local/share/boost', '/usr/share/swift',
    '/opt/hostedtoolcache',
)
CUSTOM_VARS = {
    'checkout_configuration': 'small',
    'checkout_pgo_profiles': False,
    'checkout_telemetry_dependencies': False,
    'checkout_js_coverage_modules': False,
    'skip_wpr_archives_download': True,
    'checkout_clang_coverage_tools': False,
    'checkout_clang_tidy': False,
    'checkout_clangd': False,
    'checkout_nacl': False,
}


class CommandFailed(RuntimeError):
    """A child exited unsuccessfully; distinct from resource/deadline failures."""


TRANSIENT_NETWORK_ERROR = re.compile(
    r'HTTP (?:429|500|502|503|504)|returned error: (?:429|500|502|503|504)|'
    r'Could not resolve host|Connection (?:reset|timed out)|'
    r'Remote end closed connection|TLS connection was non-properly terminated', re.I)


def require_disposable_runner(env=None, system=None, machine=None):
    env = os.environ if env is None else env
    expected = {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64'}
    if any(env.get(key) != value for key, value in expected.items()):
        raise RuntimeError('Cleanup is restricted to disposable GitHub-hosted Linux X64 runners.')
    if (system or platform.system()) != 'Linux' or (machine or platform.machine()) != 'x86_64':
        raise RuntimeError('Linux x86-64 is required.')
    event = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text())
    if event.get('repository', {}).get('private') is not False:
        raise RuntimeError('Free experiment is restricted to public repositories.')


def require_space(path, minimum):
    free = shutil.disk_usage(path).free / GIB
    if free < minimum:
        raise RuntimeError(f'Disk gate: {free:.1f} GiB free; need at least {minimum} GiB for this stage.')
    return free


def stop_process_group(process):
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


class Runner:
    def __init__(self, work, logs, budget_seconds=315 * 60):
        self.work, self.logs = work, logs
        self.deadline = time.monotonic() + budget_seconds
        self.env = dict(os.environ, DEPOT_TOOLS_UPDATE='0', DEPOT_TOOLS_METRICS='0',
                        VPYTHON_BYPASS='', DEBIAN_FRONTEND='noninteractive')
        self.state = {'status': 'running', 'stages': [], 'apk_built': False}

    def save(self):
        (self.logs / 'status.json').write_text(json.dumps(self.state, indent=2) + '\n')

    def metrics(self):
        data = {'free_gib': round(shutil.disk_usage(self.work).free / GIB, 2),
                'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        if Path('/proc/meminfo').exists():
            data['memory'] = {line.split(':')[0]: line.split(':')[1].strip()
                              for line in Path('/proc/meminfo').read_text().splitlines()
                              if line.startswith(('MemTotal:', 'MemAvailable:', 'SwapTotal:', 'SwapFree:'))}
        with (self.logs / 'resources.jsonl').open('a') as stream:
            stream.write(json.dumps(data) + '\n')
        return data

    def run(self, name, command, cwd=None, minutes=60):
        require_space(self.work, RESERVE_GIB)
        record = {'name': name, 'command': command, 'status': 'running'}
        self.state['stages'].append(record)
        self.save()
        end = min(self.deadline, time.monotonic() + minutes * 60)
        if time.monotonic() >= end:
            raise RuntimeError('Total build budget exhausted; leaving time for diagnostics upload.')
        print(f'::group::{name}', flush=True)
        log = self.logs / f'{name}.log'
        started = time.monotonic()
        process = None
        try:
            with log.open('wb') as output, log.open('rb') as reader:
                process = subprocess.Popen(command, cwd=cwd or self.work, env=self.env,
                                           stdout=output, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                next_metrics = 0
                while True:
                    chunk = reader.read(65536)
                    if chunk:
                        # Prefix to keep untrusted build output from becoming Actions commands.
                        print('build-output: ' + chunk.decode('utf-8', errors='replace').replace('\n', '\nbuild-output: '), flush=True)
                    if process.poll() is not None:
                        while True:
                            chunk = reader.read(65536)
                            if not chunk:
                                break
                            print('build-output: ' + chunk.decode('utf-8', errors='replace').replace('\n', '\nbuild-output: '), flush=True)
                        break
                    now = time.monotonic()
                    if now >= end:
                        raise RuntimeError(f'{name}: timeout; build budget is capped below six hours.')
                    if now >= next_metrics:
                        self.metrics()
                        require_space(self.work, RESERVE_GIB)
                        next_metrics = now + 30
                    time.sleep(1)
                if process.returncode:
                    raise CommandFailed(f'{name}: command failed with exit {process.returncode}. See {log.name}.')
            record['status'] = 'passed'
        except BaseException as error:
            if process is not None:
                stop_process_group(process)
            record.update(status='failed', error=str(error))
            raise
        finally:
            record['seconds'] = round(time.monotonic() - started, 1)
            self.save()
            print('::endgroup::', flush=True)

    def network(self, name, command, cwd=None, minutes=60):
        """Retry transient transport failures, retaining each attempt's diagnostics."""
        end = min(self.deadline, time.monotonic() + minutes * 60)
        for attempt in range(1, 4):
            stage = f'{name}-attempt-{attempt}'
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f'{name}: network stage budget exhausted.')
            try:
                self.run(stage, command, cwd=cwd, minutes=remaining / 60)
                return
            except CommandFailed:
                output = (self.logs / f'{stage}.log').read_text(errors='replace')
                delay = 15 * attempt
                if (attempt == 3 or not TRANSIENT_NETWORK_ERROR.search(output)
                        or time.monotonic() + delay >= end):
                    raise
                print(f'{name}: transient network failure; retrying in {delay}s.', flush=True)
                time.sleep(delay)

    def checkout(self, name, repository, revision, destination, minutes):
        # Fetch into an initialized repo so retries never need to delete a partial clone.
        self.run(f'{name}-init', ['git', 'init', str(destination)], minutes=2)
        self.run(f'{name}-remote', ['git', 'remote', 'add', 'origin', repository],
                 cwd=destination, minutes=2)
        refspec = f'{revision}:{revision}' if revision.startswith('refs/tags/') else revision
        self.network(f'{name}-fetch', ['git', 'fetch', '--depth', '1', '--no-tags',
                     'origin', refspec], cwd=destination, minutes=minutes)
        self.run(f'{name}-checkout', ['git', 'checkout', '--detach', 'FETCH_HEAD'],
                 cwd=destination, minutes=10)


SNAPCRAFT_BLOCK = 'if package_exists snapcraft; then\n    dev_list="${dev_list} snapcraft"\nfi\n'


def stage_install_scripts(src, destination):
    """Copy the Android dependency installers without snapcraft.

    snapcraft is a snap wrapper that downloads core24 from api.snapcraft.io and
    is not used by the Android build; that download timed out in run 21. The
    Chromium checkout stays untouched so prepare.py still sees clean sources.
    """
    destination.mkdir(parents=True, exist_ok=True)
    main = (src / 'build/install-build-deps.sh').read_text()
    if main.count(SNAPCRAFT_BLOCK) != 1:
        raise RuntimeError('install-build-deps.sh snapcraft block changed; review before installing.')
    (destination / 'install-build-deps.sh').write_text(main.replace(SNAPCRAFT_BLOCK, ''))
    android = destination / 'install-build-deps-android.sh'
    shutil.copy2(src / 'build/install-build-deps-android.sh', android)
    return android


# preflight: disk only; gn-only: stop after `gn gen --check`; build: compile the APK.
MODES = ('preflight', 'gn-only', 'build')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, default='build')
    parser.add_argument('--jobs', type=int, choices=(1, 2, 3, 4), default=2)
    return parser.parse_args(argv)


def compiles(mode):
    return mode == 'build'


def main():
    args = parse_args()
    require_disposable_runner()
    logs = ROOT / 'ci-logs'
    logs.mkdir(exist_ok=True)
    work = Path(os.environ['RUNNER_TEMP']) / 'sharingan-build'
    work.mkdir(exist_ok=False)
    # Preserve diagnostics on TERM and stop the entire current compile process group.
    def interrupted(signum, frame):
        raise RuntimeError(f'Runner interrupted by signal {signum}.')
    signal.signal(signal.SIGTERM, interrupted)
    runner = Runner(work, logs)
    try:
        runner.state['before_cleanup'] = runner.metrics()
        runner.save()
        for path in RECLAIM_PATHS:
            for protected in (ROOT.resolve(), work.resolve(), Path(sys.executable).resolve()):
                if protected.is_relative_to(Path(path)):
                    raise RuntimeError(f'Refusing to delete a path containing active files: {path}')
        # The normal 3 GiB reserve must not prevent cleanup on a nearly-full fresh runner.
        subprocess.run(['sudo', 'rm', '-rf', '--', *RECLAIM_PATHS], check=True)
        runner.state['after_cleanup'] = runner.metrics()
        runner.save()
        print(json.dumps(runner.state, indent=2), flush=True)
        if args.mode == 'preflight':
            runner.state['status'] = 'preflight-complete'
            runner.state['disk_gate_passed'] = shutil.disk_usage(work).free >= MIN_START_GIB * GIB
            return
        require_space(work, MIN_START_GIB)
        lock = json.loads((ROOT / 'config/upstream.lock.json').read_text())
        version = lock['chromium_version_candidate']
        depot_revision = lock['depot_tools_commit']
        depot = work / 'depot_tools'
        src = work / 'src'
        runner.checkout('01-depot',
                        'https://chromium.googlesource.com/chromium/tools/depot_tools.git',
                        depot_revision, depot, minutes=10)
        runner.env['PATH'] = str(depot) + ':' + runner.env['PATH']
        runner.checkout('04-chromium', lock['chromium_repository'],
                        f'refs/tags/{version}', src, minutes=90)
        (work / '.gclient').write_text('solutions = ' + repr([{
            'name': 'src', 'url': lock['chromium_repository'], 'managed': False,
            'custom_deps': {}, 'custom_vars': CUSTOM_VARS,
        }]) + "\ntarget_os = ['android']\n")
        runner.network('05-dependency-sync', [str(depot / 'gclient'), 'sync', '--nohooks',
                   '--no-history', '--shallow', '--jobs=2'], minutes=90)
        require_space(work, 20)
        # Chromium 105 predates install-build-deps.py. Jammy is newer than its
        # distro allowlist, but still provides libncurses5 and the i386 SDK libs.
        # Reuse download files only. APT still resolves dependencies and verifies
        # repository metadata/checksums; never restore /usr or dpkg state.
        package_cache = ROOT / '.ci-cache/apt'
        package_cache.mkdir(parents=True, exist_ok=True)
        packages = [str(p) for p in package_cache.glob('*.deb')
                    if p.is_file() and not p.is_symlink()]
        if packages:
            runner.run('06-restore-packages', ['sudo', 'cp', '--', *packages,
                       '/var/cache/apt/archives/'], minutes=3)
        runner.run('06-keep-packages', ['sudo', '/usr/bin/python3', '-c',
                   'from pathlib import Path; Path("/etc/apt/apt.conf.d/99sharingan-keep-downloads").write_text(\'APT::Keep-Downloaded-Packages "true";\\nBinary::apt::APT::Keep-Downloaded-Packages "true";\\n\')'], minutes=1)
        installer = stage_install_scripts(src, work / 'install-deps')
        runner.run('06-system-dependencies', ['bash',
                   str(installer), '--unsupported'], cwd=src, minutes=30)
        # This baseline does not provision third_party/ninja through DEPS.
        runner.run('06-ninja', ['sudo', 'apt-get', 'install', '-y', 'ninja-build'], minutes=5)
        runner.state['package_cache'] = export_packages(
            Path('/var/cache/apt/archives'), package_cache)
        runner.save()
        print('Package cache: ' + json.dumps(runner.state['package_cache']), flush=True)
        runner.run('07-apt-clean', ['sudo', 'apt-get', 'clean'], minutes=2)
        runner.run('08-hooks', [str(depot / 'gclient'), 'runhooks'], minutes=45)
        runner.run('09-overlay', ['/usr/bin/python3', str(ROOT / 'scripts/prepare.py'), str(src)], minutes=15)
        out = src / 'out/sharingan_arm64'
        shutil.copy2(ROOT / 'config/args.free.gn', out / 'args.gn')
        shutil.copy2(out / 'args.gn', logs / 'args.gn')
        shutil.copy2(work / '.gclient', logs / 'gclient.txt')
        runner.state.update(chromium_version=version, depot_revision=depot_revision,
                            kiwi_revision=lock['commit'], compile_jobs=args.jobs)
        runner.save()
        # Use the GN binary pinned by Chromium DEPS. The depot_tools wrapper
        # depends on a separate Python bootstrap that gclient need not create.
        gn = src / 'buildtools/linux64/gn'
        if not gn.is_file() or not os.access(gn, os.X_OK):
            raise RuntimeError('Chromium GN binary missing; dependency sync must install buildtools/linux64/gn.')
        runner.run('10-gn', [str(gn), 'gen', 'out/sharingan_arm64',
                   '--check', '--fail-on-unused-args'], cwd=src, minutes=10)
        if not compiles(args.mode):
            runner.state['status'] = 'gn-complete'
            return
        require_space(work, MIN_BUILD_GIB)
        runner.run('11-compile', ['/usr/bin/ninja', '-C',
                   'out/sharingan_arm64', f'-j{args.jobs}', 'chrome_public_apk'], cwd=src, minutes=300)
        apk = out / 'apks/ChromePublic.apk'
        if not apk.is_file() or apk.stat().st_size == 0:
            raise RuntimeError('Build returned successfully but APK is missing or empty.')
        artifacts = ROOT / 'ci-artifacts'
        artifacts.mkdir(exist_ok=True)
        filename = 'SharinganBrowser-dev-arm64.apk'
        shutil.copy2(apk, artifacts / filename)
        digest = hashlib.sha256(apk.read_bytes()).hexdigest()
        (artifacts / 'SHA256SUMS').write_text(f'{digest}  {filename}\n')
        runner.state.update(status='build-complete', apk_built=True, apk_sha256=digest)
    except BaseException as error:
        runner.state.update(status='failed', error=str(error))
        print(str(error), file=sys.stderr)
        raise
    finally:
        runner.metrics()
        runner.save()
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write('## Sharingan free-runner experiment\n\n')
                stream.write(f"Status: **{runner.state['status']}**. APK built: **{runner.state['apk_built']}**.\n\n")
                stream.write('Download the diagnostics artifact for per-stage logs and resource measurements.\n')
                stream.write('Compilation success does not establish Android runtime or extension compatibility.\n')

if __name__ == '__main__':
    main()
