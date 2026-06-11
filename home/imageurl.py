from ddgs import DDGS


def get_image_url(query, max_results=1):
    with DDGS() as ddgs:
        results = list(ddgs.images(query, max_results=max_results))

    if not results:
        return None

    # Usually contains fields like: image, thumbnail, title, url
    return results[0].get("image") or results[0].get("thumbnail")


if __name__ == "__main__":
    url = get_image_url("La Union Philippines beach")
    print(url)
