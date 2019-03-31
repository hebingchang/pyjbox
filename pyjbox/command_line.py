from pyjbox import jbox
import argparse

def main():
    parser = argparse.ArgumentParser(description='jBox file downloader with multiple threads and resume from break point support!',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('url', metavar='URL', type=str,
                        help='jBox share URL in following format:\n'
                             '1. https://jbox.sjtu.edu.cn/link/view/a22cc601c0f344f9bfa0eb26eda6fb68\n'
                             '2. a22cc601c0f344f9bfa0eb26eda6fb68\n'
                             '3. https://jbox.sjtu.edu.cn/l/6uq1nI\n'
                             '4. 6uq1nI')

    parser.add_argument('-c', '--connections', dest='connections', default=4, type=int,
                        help='connections while downloading (default 4)')

    parser.add_argument('-t', '--timeout', dest='timeout', default=5, type=int,
                        help='socket timeout in seconds (default 5)')

    args = parser.parse_args()

    f = jbox.JboxShare(args.url)
    f.download(connections=args.connections, timeout=args.timeout)

if __name__ == "__main__":
    main()