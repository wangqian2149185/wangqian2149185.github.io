function applyLanguage(language) {
  const lang = language === 'zh' ? 'zh' : 'en';
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  localStorage.setItem('portfolio-lang', lang);
  document.title = lang === 'zh' ? '用机制建模重新设计蛋白质 NMR 实验 | Qian Wang' : 'Using Mechanistic Modeling to Redesign a Protein NMR Experiment | Qian Wang';
  document.querySelector('.case-figure img').alt = lang === 'zh'
    ? '三条模拟 CPMG 曲线：交换速率为每秒 20,000、5,000 和 1,000。20,000 的曲线接近平坦，另两条在 80 至 1,040 Hz 范围内的变化更明显。'
    : 'Three synthetic CPMG profiles with exchange rates of 20,000, 5,000 and 1,000 per second. The 20,000 curve is nearly flat; the lower-rate curves show greater dispersion across 80 to 1,040 Hz.';
  document.querySelector('.case-evidence img').alt = lang === 'zh'
    ? '已发表的 25°C 残基 CPMG 实测曲线，含误差棒，比较两种 pH 与磁场条件。部分曲线有明显色散及拟合线，部分接近平坦或未获得可靠拟合。'
    : 'Published 25°C CPMG profiles with error bars for individual residues, comparing two pH conditions and magnetic fields. Some profiles show dispersion and fitted lines; others are flat or lack reliable fits.';
  document.querySelectorAll('[data-lang]').forEach(button => {
    button.classList.toggle('active', button.dataset.lang === lang);
    button.setAttribute('aria-pressed', String(button.dataset.lang === lang));
  });
}
function applyTheme(theme) {
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
applyLanguage(localStorage.getItem('portfolio-lang') || (navigator.language.startsWith('zh') ? 'zh' : 'en'));
applyTheme(document.documentElement.dataset.theme);
document.querySelectorAll('[data-lang]').forEach(button => button.addEventListener('click', () => applyLanguage(button.dataset.lang)));
document.querySelector('[data-theme-toggle]').addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
