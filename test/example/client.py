from coworks.cli import main
import sys

if __name__ == '__main__':
    sys.argv[1:] = ['export', '--app', 'mail', '--format', 'list']
    main()
