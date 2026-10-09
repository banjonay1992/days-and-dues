'use strict';
const screenContent = {
  today: ['Today: see unpaid invoices and quick actions for recording your day', 'Today · Your day at a glance. Example records.'],
  work: ['Work: plan projects and appointments with their clients and recorded costs', 'Work · Projects, appointments and everything in between. Example records.'],
  clients: ['Clients: see client details and the work linked to each person', 'Clients · The people behind your working day. Example records.'],
  money: ['Money: see recorded invoice revenue, expenses and outstanding amounts', 'Money · What comes in, what goes out and what’s due. Example records.']
};
const buttons = [...document.querySelectorAll('[data-screen]')];
const preview = document.getElementById('tour-image');
const caption = document.getElementById('tour-caption');
function showScreen(button) {
  const key = button.dataset.screen;
  if (!preview || !caption || !Object.hasOwn(screenContent, key)) return;
  buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  preview.src = `assets/screens/${key}.jpg`;
  [preview.alt, caption.textContent] = screenContent[key];
}
buttons.forEach((button, index) => {
  button.addEventListener('click', () => showScreen(button));
  button.addEventListener('keydown', event => {
    if (!['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (['ArrowDown','ArrowRight'].includes(event.key) ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next].focus(); showScreen(buttons[next]);
  });
});
const menu = document.querySelector('.mobile-menu');
if (menu) {
  menu.addEventListener('keydown', event => {
    if (event.key === 'Escape') { menu.open = false; menu.querySelector('summary').focus(); }
  });
}
