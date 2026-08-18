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
  const response = await fetch(`/api/jobs/${id}`);
  if (guard(response)) return;
  const job = await response.json();
  render(job);
  if (!['completed', 'human_required', 'failed'].includes(job.status)) timer = setTimeout(() => poll(id), 1500);
}

function render(job) {
  document.querySelector('#job-title').textContent = ({analyzing:'正在分析需求',generating:'正在生成测试用例',completed:'任务已完成',human_required:'需要人工介入',failed:'任务执行失败'})[job.status] || '任务排队中';
  document.querySelector('#job-message').textContent = job.message;
  document.querySelector('#status-dot').className = `status-dot ${job.status}`;
  document.querySelector('#progress-bar').style.width = ({queued:'8%',analyzing:'38%',generating:'72%',completed:'100%',human_required:'100%',failed:'100%'})[job.status] || '8%';
  if (job.status === 'human_required' || job.status === 'failed') {
    const box = document.querySelector('#human-box'); box.classList.remove('hidden'); box.textContent = job.message;
  }
  if (job.status === 'completed') {
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