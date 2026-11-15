const $ = (s) => document.querySelector(s);
const types = ['电话', '邮箱', '微信', 'QQ', '地址', '其他'];
let contacts = [];
let favoriteOnly = false;
let editingId = null;
let toastTimer;

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function toast(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 4000);
}

async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || '操作失败');
  return data;
}

async function reload() {
  contacts = await request('/api/contacts');
  render();
}

function render() {
  const keyword = $('#search').value.trim().toLocaleLowerCase();
  const list = contacts.filter(c => (!favoriteOnly || c.favorite) &&
    [c.name, c.group, ...c.methods.map(m => m.value)].join('\n').toLocaleLowerCase().includes(keyword))
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
  $('#all-count').textContent = contacts.length;
  $('#favorite-count').textContent = contacts.filter(c => c.favorite).length;
  $('#result-count').textContent = `共 ${list.length} 位联系人`;
  $('#cards').replaceChildren();
  $('#empty').hidden = list.length > 0;
  $('#empty h2').textContent = keyword ? '没有找到匹配的联系人' : favoriteOnly ? '还没有收藏联系人' : '在这里，保存你的第一份联系';
  for (const contact of list) {
    const card = node('article', undefined, 'card');
    const head = node('div', undefined, 'card-head');
    const identity = node('div');
    identity.append(node('h2', contact.name), node('span', contact.group || '未分组', 'group'));
    head.append(node('div', [...contact.name][0], 'avatar'), identity);
    const favorite = node('button', contact.favorite ? '★' : '☆', `favorite${contact.favorite ? ' selected' : ''}`);
    favorite.setAttribute('aria-label', `${contact.favorite ? '取消收藏' : '收藏'}${contact.name}`);
    favorite.setAttribute('aria-pressed', contact.favorite);
    favorite.onclick = async () => {
      favorite.disabled = true;
      try {
        await request(`/api/contacts/${contact.id}`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...contact, favorite: !contact.favorite})});
        await reload();
      } catch (error) { favorite.disabled = false; toast(error.message); }
    };
    card.append(head, favorite);
    for (const method of contact.methods.slice(0, 3)) {
      const line = node('div', undefined, 'method');
      line.append(node('small', method.type), node('span', `${method.value}${method.label ? ` · ${method.label}` : ''}`));
      card.append(line);
    }
    if (contact.methods.length > 3) card.append(node('p', `另有 ${contact.methods.length - 3} 条联系方式，点击查看全部`, 'extra'));
    const bottom = node('div', undefined, 'card-bottom');
    const edit = node('button', '查看 / 编辑', 'text-button');
    edit.onclick = () => openEditor(contact);
    const remove = node('button', '删除', 'text-button delete');
    remove.onclick = async () => {
      if (!confirm(`删除“${contact.name}”？此操作不可撤销。`)) return;
      try { await request(`/api/contacts/${contact.id}`, {method: 'DELETE'}); await reload(); toast('联系人已删除'); }
      catch (error) { toast(error.message); }
    };
    bottom.append(edit, remove);
    card.append(bottom);
    $('#cards').append(card);
  }
}

function methodRow(method = {type: '电话', label: '', value: ''}) {
  const row = node('div', undefined, 'method-row');
  const type = node('select');
  type.setAttribute('aria-label', '联系方式类型');
  for (const kind of types) { const option = node('option', kind); option.value = kind; type.append(option); }
  type.value = method.type;
  const label = node('input'); label.placeholder = '标签'; label.setAttribute('aria-label', '联系方式标签'); label.maxLength = 40; label.value = method.label;
  const value = node('input'); value.placeholder = '输入联系方式'; value.setAttribute('aria-label', '联系方式内容'); value.maxLength = 500; value.required = true; value.value = method.value;
  const remove = node('button', '×'); remove.type = 'button'; remove.setAttribute('aria-label', '移除此联系方式');
  remove.onclick = () => {
    if ($('#methods').children.length <= 1) return toast('至少保留一条联系方式');
    row.remove();
  };
  row.append(type, label, value, remove);
  $('#methods').append(row);
}

function openEditor(contact) {
  editingId = contact?.id || null;
  $('#contact-form').reset();
  $('#form-title').textContent = contact ? '编辑联系人' : '新建联系人';
  $('#form-error').textContent = '';
  for (const key of ['name', 'group', 'note']) $('#contact-form').elements[key].value = contact?.[key] || '';
  $('#contact-form').elements.favorite.checked = contact?.favorite || false;
  $('#methods').replaceChildren();
  (contact?.methods || [{type: '电话', label: '', value: ''}]).forEach(methodRow);
  $('#editor').showModal();
}

$('#add').onclick = $('#empty-add').onclick = () => openEditor();
$('#close').onclick = $('#cancel').onclick = () => $('#editor').close();
$('#add-method').onclick = () => $('#methods').children.length < 50 ? methodRow() : toast('最多 50 条联系方式');
$('#search').oninput = render;
for (const [id, only] of [['all', false], ['favorites', true]]) {
  $(`#${id}`).onclick = () => {
    favoriteOnly = only;
    $('#all').classList.toggle('active', !only);
    $('#favorites').classList.toggle('active', only);
    $('#heading').textContent = only ? '我的收藏' : '全部联系人';
    render();
  };
}

$('#contact-form').onsubmit = async event => {
  event.preventDefault();
  const form = event.target;
  const submit = form.querySelector('[type=submit]');
  const data = Object.fromEntries(['name', 'group', 'note'].map(key => [key, form.elements[key].value]));
  data.favorite = form.elements.favorite.checked;
  data.methods = [...$('#methods').children].map(row => ({type: row.children[0].value, label: row.children[1].value, value: row.children[2].value}));
  submit.disabled = true;
  try {
    await request('/api/contacts' + (editingId ? `/${editingId}` : ''), {method: editingId ? 'PUT' : 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
    $('#editor').close(); await reload(); toast('联系人已保存');
  } catch (error) { $('#form-error').textContent = error.message; }
  finally { submit.disabled = false; }
};

$('#import').onchange = async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (!file.name.toLowerCase().endsWith('.xlsx') || file.size > 5 * 1024 * 1024) throw new Error('请选择不超过 5 MB 的 .xlsx 文件');
    const result = await request('/api/import', {method: 'POST', headers: {'Content-Type': 'application/octet-stream'}, body: file});
    await reload(); toast(`成功导入 ${result.imported} 位联系人`);
  } catch (error) { toast(error.message); }
  finally { event.target.value = ''; }
};

reload().catch(error => toast(error.message));
