from desktop.app import main

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import sys
        import traceback
        from desktop.runtime import default_data_dir
        if not getattr(sys, "frozen", False):
            raise
        folder = default_data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / "startup-error.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "Mystery 无法启动。请确认已安装 Microsoft Edge WebView2 Runtime。\n\n诊断文件：" + str(log), "Mystery", 0x10)
        else:
            if sys.stderr:
                print("Mystery 启动失败，诊断文件：" + str(log), file=sys.stderr)
        raise SystemExit(1)
