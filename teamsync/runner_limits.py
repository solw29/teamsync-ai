"""Additional Unix resource ceilings. Disposable container is still required."""
import resource


def apply():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024 * 1024, 4 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


if __name__ == '__main__':
    import runpy
    import sys

    apply()
    sys.argv = ['pytest', *sys.argv[1:]]
    runpy.run_module('pytest', run_name='__main__')
