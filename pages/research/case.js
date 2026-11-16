function setCaseLanguage(language) {
  const lang = language === 'zh' ? 'zh' : 'en';
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  localStorage.setItem('portfolio-lang', lang);
  document.title = document.body.dataset[lang === 'zh' ? 'titleZh' : 'titleEn'] + ' | Qian Wang';
  document.querySelectorAll('[data-alt-en]').forEach(image => {
    image.alt = lang === 'zh' ? image.dataset.altZh : image.dataset.altEn;
  });
  document.querySelectorAll('[data-lang]').forEach(button => {
    button.classList.toggle('active', button.dataset.lang === lang);
    button.setAttribute('aria-pressed', String(button.dataset.lang === lang));
  });
}
function setCaseTheme(theme) {
  const next = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('portfolio-theme', next);
  document.querySelectorAll('img[data-theme-light-src]').forEach(image => {
    image.src = next === 'dark' ? image.dataset.themeDarkSrc : image.dataset.themeLightSrc;
  });

  const button = document.querySelector('[data-theme-toggle]');
  button.textContent = next === 'dark' ? '☀' : '☾';
  button.setAttribute('aria-label', next === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
}
setCaseLanguage(localStorage.getItem('portfolio-lang') || (navigator.language.startsWith('zh') ? 'zh' : 'en'));
setCaseTheme(document.documentElement.dataset.theme);
document.querySelectorAll('[data-lang]').forEach(button => button.addEventListener('click', () => setCaseLanguage(button.dataset.lang)));
document.querySelector('[data-theme-toggle]').addEventListener('click', () => setCaseTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
