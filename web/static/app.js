const form = document.querySelector('#upload-form');
const input = document.querySelector('#requirement');
const name = document.querySelector('#file-name');
const panel = document.querySelector('#job-panel');
const accountBtn = document.querySelector('#account-btn');
const accountModal = document.querySelector('#account-modal');
const accountClose = document.querySelector('#account-close');
const accountForm = document.querySelector('#account-form');
const accountUsername = document.querySelector('#account-username');
const accountMsg = document.querySelector('#account-msg');
let timer;

function guard(response) {
  if (response.status === 401) { location.href = '/login'; return true; }
  return false;
}

input.addEventListener('change', () => { name.textContent = input.files[0]?.name || '选择或拖入需求文档'; });
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const response = await fetch('/api/jobs', { method: 'POST', body: new FormData(form) });
  if (guard(response)) return;
  const data = await response.json();
  if (!response.ok) return alert(data.error || '提交失败');
  panel.classList.remove('hidden');
  poll(data.id);
});

async function poll(id) {
  clearTimeout(timer);
  try {
    const response = await fetch(`/api/jobs/${id}`);
    if (guard(response)) return;
    const job = await response.json();
    render(job);
    if (!['completed', 'human_required', 'failed'].includes(job.status)) timer = setTimeout(() => poll(id), 1500);
  } catch (e) {
    // 网络错误（如服务重启瞬间）时重试，避免轮询永久停止
    timer = setTimeout(() => poll(id), 3000);
  }
}

function render(job) {
  const status = job.status;
  const stages = document.querySelectorAll('.stages span[data-stage]');
  document.querySelector('#job-title').textContent = ({analyzing:'正在分析需求',generating:'正在生成测试用例',completed:'任务已完成',human_required:'需要人工介入',failed:'任务执行失败'})[status] || '任务排队中';
  document.querySelector('#job-message').textContent = job.message;
  document.querySelector('#status-dot').className = `status-dot ${status}`;
  const widths = {queued:'8%',analyzing:'38%',generating:'72%',completed:'100%',human_required:'100%',failed:'100%'};
  const bar = document.querySelector('#progress-bar');
  bar.style.width = widths[status] || '8%';
  const activeIndex = {analyzing:0, generating:1, completed:2}[status] ?? -1;
  stages.forEach((el, i) => {
    el.classList.toggle('done', activeIndex >= i);
    el.classList.toggle('active', i === activeIndex);
    if (status === 'failed' || status === 'human_required') el.classList.toggle('failed', i >= activeIndex);
  });
  if (status === 'human_required' || status === 'failed') {
    const box = document.querySelector('#human-box'); box.classList.remove('hidden'); box.textContent = job.message;
  }
  if (status === 'completed') {
    const downloads = document.querySelector('#downloads'); downloads.classList.remove('hidden');
    downloads.querySelectorAll('a').forEach(link => { link.href = `/api/jobs/${job.id}/download/${link.dataset.artifact}`; });
  }
}

accountBtn?.addEventListener('click', async () => {
  const response = await fetch('/api/account');
  if (guard(response)) return;
  const data = await response.json();
  accountUsername.value = data.username;
  accountMsg.textContent = '';
  accountModal.classList.remove('hidden');
});
accountClose?.addEventListener('click', () => accountModal.classList.add('hidden'));
accountModal?.addEventListener('click', (event) => { if (event.target === accountModal) accountModal.classList.add('hidden'); });
accountForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(accountForm));
  const response = await fetch('/api/account', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (guard(response)) return;
  const data = await response.json();
  if (!response.ok) { accountMsg.textContent = data.error || '保存失败'; return; }
  accountMsg.textContent = '已保存';
  accountForm.reset();
  accountUsername.value = data.username;
  setTimeout(() => { accountModal.classList.add('hidden'); accountMsg.textContent = ''; }, 900);
});

const statusText = {queued:'排队中',analyzing:'分析中',generating:'生成用例中',completed:'已完成',human_required:'需人工介入',failed:'失败'};

async function loadHistory() {
  const response = await fetch('/api/jobs');
  if (guard(response)) return;
  const data = await response.json();
  const list = document.querySelector('#history-list');
  const jobs = data.jobs || [];
  if (!jobs.length) { list.innerHTML = '<p class="history-empty">暂无历史任务</p>'; return; }
  list.innerHTML = jobs.map(job => {
    const ok = job.status === 'completed';
    const downloads = ok ? [
      `<a class="dl-link" href="/api/jobs/${job.id}/download/analysis">需求分析结果.md</a>`,
      `<a class="dl-link" href="/api/jobs/${job.id}/download/analysis-json">analysis.json</a>`,
      `<a class="dl-link" href="/api/jobs/${job.id}/download/test-cases-md">test_cases.md</a>`,
      `<a class="dl-link" href="/api/jobs/${job.id}/download/test-cases">test_cases.json</a>`,
    ].join('') : '<span class="dl-none">无产物</span>';
    return `<div class="history-row ${job.status}">
      <div class="history-main"><span class="history-id">${job.id}</span><span class="history-status ${job.status}">${statusText[job.status] || job.status}</span><span class="history-time">${job.updated_at || ''}</span><span class="history-msg">${job.message || ''}</span></div>
      <div class="history-downloads">${downloads}</div>
    </div>`;
  }).join('');
}

document.querySelector('#refresh-history').addEventListener('click', loadHistory);
loadHistory();