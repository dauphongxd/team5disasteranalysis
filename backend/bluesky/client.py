# bluesky_client.py
from atproto import Client, models
import threading
import time
import datetime
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# TODO: test this code didnt test yet
class BlueskyClient:
    def __init__(self, feed_uri: str):
        self.client = Client()
        self.feed_uri = feed_uri
        self._session_active = False
        self.seen_uri = []
        self.posts = []

    def login(self, handle: str, password: str) -> bool:
        """Authenticate with Bluesky service"""
        try:
            self.client.login(handle, password)
            self._session_active = True
            logger.info("Successfully logged in to Bluesky")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self._session_active = False
            return False

    def get_feed(self, limit: int = 30) -> Optional[Dict[str, Any]]:
        """Retrieve posts from configured feed"""
        try:
            response = self.client.app.bsky.feed.get_feed(
                params={'feed': self.feed_uri, 'limit': limit}
            )
            return self._parse_feed_response(response)
        except Exception as e:
            logger.error(f"Error fetching feed: {e}")
            return None

    def get_timeline(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Fallback method to get user timeline"""
        try:
            response = self.client.app.bsky.feed.get_timeline({'limit': limit})
            return self._parse_feed_response(response)
        except Exception as e:
            logger.error(f"Error fetching timeline: {e}")
            return None

    def _parse_feed_response(self, response) -> Dict[str, Any]:
        """Parse common feed response structure"""
        parsed = {
            'posts': [],
            'cursor': None,
            'timestamp': datetime.datetime.now().isoformat()
        }

        if not response or not hasattr(response, 'feed'):
            return parsed

        for post in response.feed:
            if post.post.uri in self.seen_uri:
                continue
            else: 
                self.seen_uri.append(post.post.uri)
            try:
                parsed_post = {
                    'uri': post.post.uri,
                    'author': {
                        'did': post.post.author.did,
                        'handle': post.post.author.handle,
                        'display_name': post.post.author.display_name or '',
                        'avatar_url': post.post.author.avatar or ''
                    },
                    'text': post.post.record.text,
                    'created_at': post.post.record.created_at,
                    'indexed_at': post.post.indexed_at,
                    'media_urls': []
                }

                if hasattr(post.post.record, 'embed') and hasattr(post.post.record.embed, 'images'):
                    parsed_post['media_urls'] = [
                        f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                        for image in post.post.record.embed.images
                        if hasattr(image.image.ref, 'link')
                    ]

                parsed['posts'].append(parsed_post)
                self.posts.append(parsed_post)
            except Exception as e:
                logger.error(f"Error parsing post: {e}")

        if hasattr(response, 'cursor'):
            parsed['cursor'] = response.cursor

        return parsed

    def maintain_session(self, handle: str, password: str) -> bool:
        """Maintain active session with Bluesky"""
        try:
            self.client.app.bsky.actor.get_profile({'actor': handle})
            return True
        except Exception as e:
            logger.warning(f"Session validation failed: {e}")
            return self.login(handle, password)

if __name__ == "__main__":
    FEED_URI = 'at://did:plc:qiknc4t5rq7yngvz7g4aezq7/app.bsky.feed.generator/aaaelfwqlfugs'
    client = BlueskyClient(FEED_URI)
    client.login("capt-vikram.bsky.social", "DQEcAf9YNS8m25r")

    
    def keep_session_alive():
        """Background thread to keep the Bluesky session alive"""
        while True:
            try:
                time.sleep(600)  # Check every 10 minutes
                logger.info("Performing session health check")
                handle = "capt-vikram.bsky.social" 
                client.app.bsky.actor.get_profile({'actor': handle})
                logger.info("Session is still valid")
            except Exception as e:
                logger.warning(f"Session error in monitor thread: {e}")
                try:
                    logger.info("Refreshing session from background thread")
                    client.login("capt-vikram.bsky.social", "DQEcAf9YNS8m25r")
                    logger.info("Session refreshed successfully")
                except Exception as login_error:
                    logger.error(f"Failed to refresh session: {login_error}")

    # Start the thread as daemon so it exits when main thread exits
    session_thread = threading.Thread(target=keep_session_alive, daemon=True)
    session_thread.start()
    feed = client.get_feed()
    print(len(client.posts))
