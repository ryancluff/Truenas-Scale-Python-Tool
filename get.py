from nas import Nas
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='setup truenas instance'
    )
    parser.add_argument(
        '--url',
        required=True,
        help=''
    )
    parser.add_argument(
        '--username',
        required=True,
        help='username of existing truenas user w/ the proper permissions'
    )
    parser.add_argument(
        '--password',
        required=True,
        help='password of the truenas user'
    )
    parser.add_argument(
        '--method',
        required=True,
        help='method to execute'
    )
    parser.add_argument(
        '--debug',
        action="store_true",
        help='enable debug stack trace'
    )
    args = parser.parse_args()

    nas = Nas(args.url)
    nas.debug = args.debug

    nas.connect(args.username, args.password)

    # nas.import_pools()
    result = nas.method(args.method, [])

    nas.disconnect()

    Nas.write_file("result.json", result)


if __name__ == "__main__":
    main()