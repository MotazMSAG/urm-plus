init 999 python:

    # The build copies this same version to the first lines of URM_fix.bat.
    # Keep this in sync with the stable release tag.
    URMU_VERSION = "1.0.0"
    _URMU_REPO = "https://github.com/MotazMSAG/urm-plus"
    _URMU_LATEST = "https://api.github.com/repos/MotazMSAG/urm-plus/releases/latest"
    _URMU_ASSET_HOSTS = ("release-assets.githubusercontent.com", "objects.githubusercontent.com",
                         "github-releases.githubusercontent.com")
    _URMU_MAX_INSTALLER = 32 * 1024 * 1024

    class _URMUState(python_object):
        def __init__(self):
            self.started = False
            self.status = "unchecked"
            self.release = None
            self.dialog = None
            self.download_pending = None

    def _urmu_state():
        return _urm_kept("update", _URMUState)

    def _urmu_version(tag):
        import re
        if not isinstance(tag, type(u"")) and not isinstance(tag, str):
            return None
        match = re.match(r"v?(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\Z", tag)
        return tuple(int(part) for part in match.groups()) if match else None

    def _urmu_release(data, installed):
        """An immutable version, tag, asset URL, length and SHA-256 from GitHub."""
        import re
        if data.get("draft") is not False or data.get("prerelease") is not False:
            return None
        tag = data.get("tag_name")
        latest = _urmu_version(tag)
        if latest is None or latest <= _urmu_version(installed):
            return None
        url = _URMU_REPO + "/releases/download/" + tag + "/URM_fix.bat"
        for asset in data.get("assets", ()):
            if (asset.get("name") != "URM_fix.bat" or asset.get("state") != "uploaded"
                    or asset.get("browser_download_url") != url):
                continue
            digest, size = asset.get("digest"), asset.get("size")
            if (isinstance(size, int) and 0 < size <= _URMU_MAX_INSTALLER and digest
                    and re.match(r"sha256:[0-9a-f]{64}\Z", digest)):
                return ("%d.%d.%d" % latest, tag, url, size, digest[7:])
        raise ValueError("The published installer has no verified asset metadata.")

    def _urmu_url(url):
        try:
            from urllib.parse import urlsplit
        except ImportError:
            from urlparse import urlsplit
        return urlsplit(url)

    def _urmu_allowed_redirect(url):
        parts = _urmu_url(url)
        return parts.scheme == "https" and parts.netloc in _URMU_ASSET_HOSTS

    def _urmu_fetch(url, limit, asset=False):
        """TLS-verified HTTPS, bounded response, with redirects only for release files."""
        parts = _urmu_url(url)
        if parts.scheme != "https" or parts.netloc != ("github.com" if asset else "api.github.com"):
            raise ValueError("Untrusted update address.")
        if _urm_os.name == "nt":
            return _urmu_fetch_windows(url, limit, asset)
        return _urmu_fetch_python(url, limit, asset)

    def _urmu_fetch_python(url, limit, asset):
        import ssl
        try:
            from urllib import request as http
        except ImportError:
            import urllib2 as http

        class ReleaseRedirect(http.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                if not asset or not _urmu_allowed_redirect(newurl):
                    raise ValueError("Untrusted update redirect.")
                return http.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)

        opener = http.build_opener(http.HTTPSHandler(context=ssl.create_default_context()), ReleaseRedirect())
        request = http.Request(url, headers=python_dict((("User-Agent", "URM-Plus/" + URMU_VERSION),)))
        if not asset:
            request.add_header("Accept", "application/vnd.github+json")
            request.add_header("X-GitHub-Api-Version", "2022-11-28")
        response = opener.open(request, timeout=8)
        try:
            content = response.read(limit + 1)
            if len(content) > limit:
                raise ValueError("Update response exceeded its expected size.")
            return content
        finally:
            response.close()

    # Ren'Py ships Python 2 without _ssl on 7.3.5, and other engines can
    # start with empty CA roots. Windows' own client uses the system trust
    # store. Each invocation makes one request. Python checks every hop.
    _URMU_HTTPS = r'''
    $ErrorActionPreference = 'Stop'
    $request = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@REQUEST@')) | ConvertFrom-Json
    Add-Type -AssemblyName System.Net.Http
    $handler = New-Object Net.Http.HttpClientHandler
    $handler.AllowAutoRedirect = $false
    $handler.UseCookies = $false
    $handler.UseDefaultCredentials = $false
    $client = New-Object Net.Http.HttpClient($handler)
    try {
        $client.Timeout = [TimeSpan]::FromSeconds(12)
        $client.DefaultRequestHeaders.UserAgent.ParseAdd($request.agent)
        if (!$request.asset) {
            $client.DefaultRequestHeaders.Accept.ParseAdd('application/vnd.github+json')
            $client.DefaultRequestHeaders.Add('X-GitHub-Api-Version', '2022-11-28')
        }
        $response = $client.GetAsync([string]$request.url, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        try {
            $status = [int]$response.StatusCode
            if ($status -eq 200) {
                $limit = [int]$request.limit
                if ($response.Content.Headers.ContentLength -gt $limit) { throw 'Update response too large' }
                $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
                $file = [IO.File]::Open($request.body, [IO.FileMode]::CreateNew)
                try {
                    $buffer = New-Object byte[] 65536
                    $size = 0
                    while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                        $size += $read
                        if ($size -gt $limit) { throw 'Update response too large' }
                        $file.Write($buffer, 0, $read)
                    }
                } finally { $file.Dispose(); $stream.Dispose() }
            }
            $location = if ($response.Headers.Location) { $response.Headers.Location.OriginalString } else { '' }
            [IO.File]::WriteAllText($request.status, "$status`n$location")
        } finally { $response.Dispose() }
    } finally { $client.Dispose() }
    '''

    def _urmu_fetch_windows(url, limit, asset):
        import tempfile
        import time
        folder = tempfile.mkdtemp(prefix="urm-plus-https-")
        body = _urm_os.path.join(folder, "body")
        status = _urm_os.path.join(folder, "status")
        try:
            for _hop in (0, 1, 2, 3):
                helper = _urmu_powershell(_URMU_HTTPS, url=url, limit=limit, asset=asset,
                                          agent="URM-Plus/" + URMU_VERSION, body=body, status=status)
                end = time.time() + 45
                while helper.poll() is None and time.time() < end:
                    time.sleep(0.025)
                if helper.poll() is None:
                    helper.terminate()
                    helper.wait()
                    raise ValueError("Update request timed out.")
                if helper.returncode != 0:
                    raise ValueError("Windows could not complete the HTTPS request.")
                with open(status, "rb") as result:
                    code, location = result.read(16384).decode("utf-8").split("\n", 1)
                if code == "200":
                    with open(body, "rb") as response:
                        data = response.read(limit + 1)
                    if len(data) > limit:
                        raise ValueError("Update response exceeded its expected size.")
                    return data
                if not asset or code not in ("301", "302", "303", "307", "308"):
                    raise ValueError("GitHub returned HTTP " + code)
                if not _urmu_allowed_redirect(location):
                    raise ValueError("Untrusted update redirect.")
                url = location
            raise ValueError("Too many update redirects.")
        finally:
            for piece in (body, status):
                if _urm_os.path.isfile(piece):
                    _urm_os.remove(piece)
            _urm_os.rmdir(folder)

    def _urmu_request():
        import json
        try:
            body = _urmu_fetch(_URMU_LATEST, 512 * 1024)
            return ("checked", _urmu_release(json.loads(body.decode("utf-8")), URMU_VERSION))
        except Exception:
            return ("offline", None)

    def _urmu_refresh():
        if (renpy.get_screen("urmu_dialog", layer=_urmi_layer) is not None
                or (_urmh_state().section == "updates"
                    and renpy.get_screen("urmh_settings", layer=_urmi_layer) is not None)):
            renpy.restart_interaction()

    def _urmu_show(which):
        _urmu_state().dialog = which
        if renpy.get_screen("urmu_dialog", layer=_urmi_layer) is None:
            renpy.show_screen("urmu_dialog", _layer=_urmi_layer)
        renpy.restart_interaction()

    def _urmu_checked(result, startup):
        state = _urmu_state()
        state.status, state.release = result or ("offline", None)
        if startup and state.release is not None and state.dialog is None:
            version = state.release[0]
            seen = _urmu_version(getattr(_urm_persistent(), "_urm_update_seen", None))
            if seen is None or seen < _urmu_version(version):
                _urmu_show("notice")
                _urm_persistent()._urm_update_seen = version
                return
        _urmu_refresh()

    def _urmu_check(startup=False):
        state = _urmu_state()
        if state.status == "checking" or state.dialog is not None:
            return
        state.status = "checking"
        _urm_work_thread("update check", _urmu_request,
                         lambda result: _urmu_checked(result, startup), blocking_io=True)

    def _urmu_on_startup():
        state = _urmu_state()
        if state.started or renpy.game.context().init_phase or not renpy.has_screen("urmu_dialog"):
            return
        state.started = True
        _urmu_check(startup=True)

    def _urmu_settings_open():
        if _urmu_state().status == "unchecked":
            _urmu_check()

    def _urmu_badge():
        if _urmu_state().release is not None:
            return ("Update available", "gain")
        return None

    def _urmu_can_apply():
        return _urm_os.name == "nt"

    def _urmu_page():
        release = _urmu_state().release
        return _URMU_REPO + ("/releases/tag/" + release[1] if release else "/releases")

    def _urmu_review():
        if _urmu_state().release is not None:
            _urmu_show("confirm" if _urmu_can_apply() else "manual")

    def _urmu_cancel():
        state = _urmu_state()
        if state.dialog in ("handoff", "closing"):
            return
        state.dialog = None
        renpy.hide_screen("urmu_dialog", layer=_urmi_layer)
        renpy.restart_interaction()

    def _urmu_stage(release):
        """Verify the bytes before writing an executable file to private staging."""
        import hashlib
        import tempfile
        version, _tag, url, size, digest = release
        contents = _urmu_fetch(url, size, asset=True)
        marker = ("rem URMPLUS_VERSION=" + version).encode("ascii")
        if (len(contents) != size or hashlib.sha256(contents).hexdigest() != digest
                or marker not in contents[:256].splitlines()):
            raise ValueError("The installer did not match the published release.")
        folder = tempfile.mkdtemp(prefix="urm-plus-update-")
        path = _urm_os.path.join(folder, "URM_fix.bat")
        try:
            with open(path, "wb") as installer:
                installer.write(contents)
        except Exception:
            _urmu_discard(path)
            raise
        return path

    def _urmu_discard(path):
        folder = _urm_os.path.dirname(path)
        for name in (_urm_os.path.basename(path), "helper.ready", "helper.error"):
            entry = _urm_os.path.join(folder, name)
            if _urm_os.path.isfile(entry):
                _urm_os.remove(entry)
        _urm_os.rmdir(folder)

    # Only the installer gets a cmd command line. The two paths are passed as
    # child environment data and expand once inside quotes, with AutoRun and
    # delayed expansion off. The ready message means the helper has opened the
    # exact parent process handle and can wait for it before starting the BAT.
    _URMU_HANDOFF = r'''
    $ErrorActionPreference = 'Stop'
    $argsData = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@REQUEST@')) | ConvertFrom-Json
    $bat = $argsData.bat
    $folder = [IO.Path]::GetDirectoryName($bat)
    $receipt = [IO.Path]::Combine($folder, 'helper.ready')
    $ready = $false
    try {
        $origin = [Diagnostics.Process]::GetProcessById($argsData.pid)
        $null = $origin.Handle
        $start = New-Object Diagnostics.ProcessStartInfo
        $start.FileName = [IO.Path]::Combine([Environment]::SystemDirectory, 'cmd.exe')
        $start.Arguments = '/d /v:off /s /c ""%URMPLUS_UPDATE_BAT%" "%URMPLUS_UPDATE_GAME%" install"'
        $start.WorkingDirectory = [IO.Path]::GetDirectoryName($bat)
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.EnvironmentVariables['URMPLUS_UPDATE_BAT'] = $bat
        $start.EnvironmentVariables['URMPLUS_UPDATE_GAME'] = $argsData.game
        if (![IO.Directory]::Exists([IO.Path]::Combine($argsData.game, 'game'))) { throw 'Game folder missing' }
        [IO.File]::WriteAllText($receipt, '')
        $ready = $true
        $origin.WaitForExit()

        $sha = [Security.Cryptography.SHA256]::Create()
        $file = [IO.File]::OpenRead($bat)
        try { $hash = [BitConverter]::ToString($sha.ComputeHash($file)).Replace('-', '').ToLowerInvariant() }
        finally { $file.Dispose(); $sha.Dispose() }
        if ($hash -cne $argsData.digest) { throw 'Installer verification failed' }
        $install = [Diagnostics.Process]::Start($start)
        $install.WaitForExit()
        if ($install.ExitCode -ne 0) { throw 'Installer failed' }
    } catch {
        if ($ready) {
            Add-Type -AssemblyName System.Windows.Forms
            $null = [Windows.Forms.MessageBox]::Show("MRM couldn't install the update. Reopen the game to retry in Settings, or get the installer from the release page.", 'MRM update')
        } else {
            [IO.File]::WriteAllText([IO.Path]::Combine($folder, 'helper.error'), $_.Exception.Message)
        }
        exit 1
    } finally {
        if ($ready) {
            [IO.File]::Delete($receipt)
            [IO.File]::Delete($bat)
            [IO.Directory]::Delete($folder)
        }
    }
    '''

    def _urmu_powershell(source, **request):
        import base64
        import ctypes
        import json
        import subprocess
        import sys
        system = ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetSystemDirectoryW(system, len(system)):
            raise ctypes.WinError()
        shell = _urm_os.path.join(system.value, "WindowsPowerShell", "v1.0", "powershell.exe")
        filesystem = sys.getfilesystemencoding()
        for key, value in request.items():
            if isinstance(value, bytes):
                request[key] = value.decode(filesystem)
        binary = json.dumps(request).encode("utf-8")
        script = source.replace("@REQUEST@", base64.b64encode(binary).decode("ascii"))
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return subprocess.Popen((shell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded),
                                cwd=system.value, close_fds=True, creationflags=0x08000200)

    def _urmu_handoff(path, pid, game, digest):
        import time
        helper = _urmu_powershell(_URMU_HANDOFF, bat=path, game=game, pid=pid, digest=digest)
        folder = _urm_os.path.dirname(path)
        receipt = _urm_os.path.join(folder, "helper.ready")
        end = time.time() + 15
        while helper.poll() is None:
            if _urm_os.path.isfile(receipt):
                return True
            if time.time() >= end:
                helper.terminate()
                helper.wait()
                break
            time.sleep(0.025)
        error = _urm_os.path.join(folder, "helper.error")
        if _urm_os.path.isfile(error):
            with open(error, "rb") as info:
                raise ValueError(info.read(200).decode("utf-8", "replace"))
        raise ValueError("The installer could not wait for the game to close.")

    def _urmu_ready(ok):
        _urmu_state().dialog = "closing" if ok else "failed"
        _urmu_refresh()

    def _urmu_staged(path, target, release):
        state = _urmu_state()
        state.download_pending = None
        if state.dialog != "downloading" or state.release != release:
            if path:
                _urm_work_thread("discard update", lambda: _urmu_discard(path), blocking_io=True)
            if state.dialog == "downloading":
                _urmu_download(state.release)
            return
        if not path:
            _urmu_ready(False)
            return
        state.dialog = "handoff"

        def handoff():
            try:
                return _urmu_handoff(path, target[0], target[1], release[4])
            except Exception:
                if _urm_os.path.isfile(path):
                    _urmu_discard(path)
                raise

        _urm_work_thread("start installer", handoff, _urmu_ready, blocking_io=True)
        _urmu_refresh()

    def _urmu_install():
        state = _urmu_state()
        if state.dialog not in ("confirm", "failed") or not state.release or not _urmu_can_apply():
            return
        state.dialog = "downloading"
        if state.download_pending is None:
            _urmu_download(state.release)
        _urmu_refresh()

    def _urmu_download(release):
        target = (_urm_os.getpid(), config.basedir)
        _urmu_state().download_pending = release
        _urm_work_thread("download update", lambda: _urmu_stage(release),
                         lambda path: _urmu_staged(path, target, release), blocking_io=True)

    def _urmu_close_for_install():
        # The work queue catches exceptions from finish callbacks. Ren'Py uses
        # a QuitException for a normal close, so send it from its own callback.
        if _urmu_state().dialog == "closing":
            _urmu_state().dialog = "handoff"
            renpy.hide_screen("urmu_dialog", layer=_urmi_layer)
            if renpy.get_screen("urmh_settings", layer=_urmi_layer) is not None:
                urmh_settings_close()
            renpy.quit(save=False)

    _urm_section_add("updates", "Updates", u"\ue923", order=90, screen="urmu_settings",
                     on_open=_urmu_settings_open, badge=_urmu_badge)
    config.interact_callbacks.append(_urmu_on_startup)
    config.periodic_callbacks.append(_urmu_close_for_install)
