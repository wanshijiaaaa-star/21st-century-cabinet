export const RES_BASE_URL = "/static/res/logo/"
export const Avatar = (url) => {
  // if (url.startsWith('http://') || url.startsWith('https://')) {
  //     return `${RES_BASE_URL}${url}`;
  //   }
    return url;
}
export const ProxyImage=(content) =>{
  return content;
  //  return content.replace(
  //     /(<img[^>]*src=["'])(https?:\/\/[^"']*)/g,
  //      '$1/static/res/logo/$2').replace(/<img([^>]*)width=["'][^"']*["']([^>]*)>/g, '<img$1$2>');
}