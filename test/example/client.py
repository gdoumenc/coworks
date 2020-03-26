from coworks.cli import main
import sys

if __name__ == '__main__':
    # sys.argv[1:] = ['export', '--app', 'mail', '--format', 'list']
    sys.argv[1:] = ['run', '-m', 'test_app', '-a', 'biz_app']
    main()
