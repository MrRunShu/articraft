class ArticleConstant:
    SSE_TIMEOUT_MS = 30 * 60 * 1000
    SSE_RECONNECT_TIME_MS = 3000

    PEXELS_API_URL = "https://api.pexels.com/v1/search"
    PEXELS_PER_PAGE = 1
    PEXELS_ORIENTATION_LANDSCAPE = "landscape"

    PICSUM_URL_TEMPLATE = "https://picsum.photos/800/600?random={}"

    # Day 8：并行配图默认配置
    AGENT_IMAGE_MAX_CONCURRENCY = 3
    AGENT_IMAGE_FAIL_FAST = True
