# TODO: implement real-time file watcher using watchfiles
# TODO: emit events when .py files are created or deleted
# FIXME: currently no debounce — rapid saves will flood the tick queue
# HACK: using pathlib mtime poll instead of inotify/FSEvents
