from localditado.hardware import Hardware, choose_compute_type, choose_device, choose_model
from localditado.platform.hotkey import normalize_hotkey


def test_normalize_hotkey_basic():
    assert normalize_hotkey("Ctrl+Alt+D") == "<ctrl>+<alt>+d"


def test_normalize_hotkey_aliases():
    assert normalize_hotkey("win+shift+s") == "<cmd>+<shift>+s"
    assert normalize_hotkey("Command+Space") == "<cmd>+<space>"


def test_normalize_hotkey_function_key():
    assert normalize_hotkey("ctrl+f2") == "<ctrl>+<f2>"


def test_choose_model_respects_explicit():
    hw = Hardware(has_cuda=True, cuda_devices=1, vram_mb=24000, cpu_count=16)
    assert choose_model("small", hw) == "small"


def test_choose_model_auto_gpu_turbo():
    hw = Hardware(has_cuda=True, cuda_devices=1, vram_mb=12000, cpu_count=16)
    assert choose_model("auto", hw) == "large-v3-turbo"


def test_choose_model_auto_small_gpu_falls_back():
    hw = Hardware(has_cuda=True, cuda_devices=1, vram_mb=3000, cpu_count=8)
    assert choose_model("auto", hw) == "small"


def test_choose_model_auto_cpu():
    hw = Hardware(has_cuda=False, cuda_devices=0, vram_mb=0, cpu_count=4)
    assert choose_model("auto", hw) == "base"


def test_choose_device_and_compute_auto():
    hw_gpu = Hardware(has_cuda=True, cuda_devices=1, vram_mb=8000, cpu_count=8)
    hw_cpu = Hardware(has_cuda=False, cuda_devices=0, vram_mb=0, cpu_count=8)
    assert choose_device("auto", hw_gpu) == "cuda"
    assert choose_device("auto", hw_cpu) == "cpu"
    assert choose_compute_type("auto", "cuda") == "int8_float16"
    assert choose_compute_type("auto", "cpu") == "int8"
