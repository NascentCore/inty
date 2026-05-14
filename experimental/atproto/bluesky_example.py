from atproto import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def bluesky_example():
    # Initialize the client
    client = Client()

    # Login to Bluesky
    client.login(
        os.getenv("BLUESKY_USERNAME"),  # Your handle or email
        os.getenv("BLUESKY_PASSWORD"),  # Your app password
    )

    # Create a post
    post = client.send_post(text="Hello from atproto! This is a test post.")
    print(f"Posted successfully! Post URI: {post.uri}")

    # Get your timeline
    timeline = client.get_timeline()
    print("\nRecent posts in your timeline:")
    for feed_view in timeline.feed[:3]:  # Show first 3 posts
        post = feed_view.post
        print(f"- {post.author.handle}: {post.record.text}")

    # Get your profile
    profile = client.get_profile(client.me.did)  # Pass the DID string directly
    print("\nYour profile:")
    print(f"Handle: {profile.handle}")
    print(f"Display Name: {profile.display_name}")
    print(f"Description: {profile.description}")


if __name__ == "__main__":
    bluesky_example()
