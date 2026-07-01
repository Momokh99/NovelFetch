from sources.royalroad import RoyalRoadSource

rr = RoyalRoadSource()
soup = rr.fetch_url("https://www.royalroad.com/fictions/best-rated")
novels = rr.extract_novel_rows(soup)
print(f"Found {len(novels)} novels")
if novels:
    for n in novels[:3]:
        print(n)
