from vk_task import FriendsParser
import argparse


parser = argparse.ArgumentParser(description="VK friends parser")
parser.add_argument("user_id", type=int, help="VK user ID")
parser.add_argument("access_token", type=str, help="VK API access token")
parser.add_argument(
    "--output_format",
    type=str,
    choices=["csv", "json", "tsv", "yaml"],
    default="csv",
    help="Output file format"
)
parser.add_argument(
    "--output_name",
    type=str,
    default="report",
    help="Output file name"
)

if __name__ == '__main__':
    args = parser.parse_args()
    vk_parser = FriendsParser(args.user_id, args.access_token, args.output_format, args.output_name)
    friends = vk_parser.parse()
    vk_parser.create_report(friends)
