import { trans as translate } from "./i18n/index.js";
import { ref, watchEffect } from "vue";

const Has_Change = () => {
  let _hash = hash(document.body.innerText);
  console.log(get_hash(), _hash);
  return get_hash() !== _hash;
};

export const hash = (str: string): string => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash.toString();
};
const key = "c-Hash-Body";
export const set_hash = (): void => {
  localStorage.setItem(key, hash(document.body.innerText));
};

export const get_hash = (): string | null => {
  return localStorage.getItem(key);
};

export const translatePage = () => {
  const savedLanguage = localStorage.getItem("language");
  if (savedLanguage) {
    setTimeout(() => {
      if (!Has_Change()) {
        console.log("未改变");
        return;
      }
      translate.changeLanguage(savedLanguage);
      set_hash();
    }, 1000); // 延时1000毫秒后执行语言切换
  }
};

export const setCurrentLanguage = (language: string) => {
  translate.changeLanguage(language);
  localStorage.setItem("language", language);
};
