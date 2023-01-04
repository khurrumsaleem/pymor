import importlib
import shutil


def setup(app):
    to_copy_files = ["standalone.js", "require.js"]
    copied = []
    for fn in to_copy_files:
        for package_fn in importlib.metadata.files("k3d"):
            if fn in str(package_fn):
                shutil.copy(package_fn.locate(), './source/_static/')
                copied.append(fn)
                break
    assert copied == to_copy_files, copied

    try:
        app.add_javascript('require.js')
        app.add_javascript('standalone.js?k3d')
    except AttributeError:
        app.add_js_file('require.js')
        app.add_js_file('standalone.js?k3d')
