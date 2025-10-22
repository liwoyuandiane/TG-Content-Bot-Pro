// TG API 代理 Worker
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // 处理 Telegram Bot API 请求
    const telegramAPI = 'https://api.telegram.org';
    
    // 构造目标 URL
    const targetURL = telegramAPI + url.pathname + url.search;
    
    // 创建新的请求
    const newRequest = new Request(targetURL, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    });
    
    // 发送请求并返回响应
    const response = await fetch(newRequest);
    
    // 创建新的响应并返回
    const newResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    });
    
    return newResponse;
  }
};