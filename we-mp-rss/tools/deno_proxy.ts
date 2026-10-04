/**
 * Deno Deploy 代理脚本
 * 
 * 部署方式：
 * 1. 在 https://dash.deno.com 创建新项目
 * 2. 将此文件作为入口点部署
 * 3. 获取部署后的 URL，配置到 config.yaml 的 proxy.deno_url
 * 
 * 使用方式：
 * - 访问: https://your-proxy.deno.dev/?url=https://example.com
 * - 或通过 POST 请求体传递 URL
 */

const ALLOWED_DOMAINS = [
  "mp.weixin.qq.com",
  "weixin.qq.com",
  "mmbiz.qpic.cn",
  "mmbiz.qlogo.cn",
];

const ALLOWED_ORIGINS = [
  "*",  // 允许所有来源，生产环境建议限制
];

function isAllowedDomain(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ALLOWED_DOMAINS.some(domain => 
      parsed.hostname === domain || parsed.hostname.endsWith('.' + domain)
    );
  } catch {
    return false;
  }
}

function corsHeaders(origin: string): HeadersInit {
  const allowedOrigin = ALLOWED_ORIGINS.includes("*") 
    ? "*" 
    : (ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0]);
  
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Cookie, User-Agent",
    "Access-Control-Expose-Headers": "Content-Type, Content-Length",
    "Access-Control-Max-Age": "86400",
  };
}

async function handleRequest(request: Request): Promise<Response> {
  const origin = request.headers.get("Origin") || "";
  
  // 处理预检请求
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(origin),
    });
  }

  let targetUrl: string | null = null;

  // 从查询参数获取 URL
  const url = new URL(request.url);
  targetUrl = url.searchParams.get("url");

  // 从 POST body 获取 URL
  if (!targetUrl && request.method === "POST") {
    try {
      const body = await request.json();
      targetUrl = body.url;
    } catch {
      // ignore
    }
  }

  if (!targetUrl) {
    return new Response(JSON.stringify({ error: "Missing 'url' parameter" }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
        ...corsHeaders(origin),
      },
    });
  }

  // 验证目标 URL
  if (!isAllowedDomain(targetUrl)) {
    return new Response(JSON.stringify({ 
      error: "Domain not allowed",
      allowed_domains: ALLOWED_DOMAINS 
    }), {
      status: 403,
      headers: {
        "Content-Type": "application/json",
        ...corsHeaders(origin),
      },
    });
  }

  try {
    // 构建请求头
    const headers = new Headers();
    
    // 转发原始请求头
    const forwardHeaders = ["User-Agent", "Cookie", "Authorization", "Accept", "Accept-Language"];
    for (const h of forwardHeaders) {
      const value = request.headers.get(h);
      if (value) {
        headers.set(h, value);
      }
    }
    
    // 设置默认 User-Agent
    if (!headers.has("User-Agent")) {
      headers.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
    }

    // 发起请求
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      redirect: "follow",
    });

    // 获取响应内容
    const contentType = response.headers.get("Content-Type") || "text/html";
    
    // 处理不同类型的响应
    let body: ArrayBuffer | string;
    if (contentType.includes("image/")) {
      body = await response.arrayBuffer();
    } else {
      body = await response.text();
    }

    // 构建响应头
    const responseHeaders = new Headers(corsHeaders(origin));
    responseHeaders.set("Content-Type", contentType);
    
    // 对于图片，添加缓存头
    if (contentType.includes("image/")) {
      responseHeaders.set("Cache-Control", "public, max-age=86400");
    }

    return new Response(body, {
      status: response.status,
      headers: responseHeaders,
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    return new Response(JSON.stringify({ 
      error: "Failed to fetch",
      message: errorMessage 
    }), {
      status: 502,
      headers: {
        "Content-Type": "application/json",
        ...corsHeaders(origin),
      },
    });
  }
}

Deno.serve(handleRequest);
