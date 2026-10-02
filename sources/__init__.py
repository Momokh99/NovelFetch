from sources.novelfire import NovelFireSource
from sources.novelphoenix import NovelPhoenixSource
from sources.royalroad import RoyalRoadSource
from sources.scriblehub import ScribbleHubSource
from sources.wuxiaspot import WuxiaSpotSource

REGISTRY = {
    "novelfire": NovelFireSource(),
    "novelphoenix": NovelPhoenixSource(),
    "royalroad": RoyalRoadSource(),
    "scribblehub": ScribbleHubSource(),
    "wuxiaspot": WuxiaSpotSource(),
}
