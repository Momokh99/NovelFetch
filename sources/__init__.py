from sources.novelfire import NovelFireSource
from sources.royalroad import RoyalRoadSource
from sources.scriblehub import ScribbleHubSource
from sources.wuxiaspot import WuxiaSpotSource

REGISTRY = {
    "novelfire": NovelFireSource(),
    "royalroad": RoyalRoadSource(),
    "scribblehub": ScribbleHubSource(),
    "wuxiaspot": WuxiaSpotSource(),
}
