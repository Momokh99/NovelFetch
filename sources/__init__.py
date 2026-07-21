from sources.royalroad import RoyalRoadSource
from sources.scriblehub import ScribbleHubSource
from sources.wuxiaspot import WuxiaSpotSource

REGISTRY = {
    "royalroad": RoyalRoadSource(),
    "scriblehub": ScribbleHubSource(),
    "wuxiaspot": WuxiaSpotSource(),
}
