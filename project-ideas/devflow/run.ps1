# DevFlow launcher — suppresses WebEngine GPU noise
$env:QTWEBENGINE_DISABLE_SANDBOX = "1"
$env:QTWEBENGINE_CHROMIUM_FLAGS = "--disable-gpu --in-process-gpu --use-gl=swiftshader-webgl"
python main.py 2>&1 | Where-Object {
    $_ -notmatch "GLES3|GLES2|GPUInfo|gpu_channel|ContextResult|kFatalFailure|Sandboxing disabled|fonts\."
}
