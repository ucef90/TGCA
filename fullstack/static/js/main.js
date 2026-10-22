'use strict';
const toggle=document.querySelector('.nav-toggle');
const nav=document.querySelector('#site-nav');
if(toggle && nav){
  toggle.addEventListener('click',()=>{
    const expanded=toggle.getAttribute('aria-expanded')==='true';
    toggle.setAttribute('aria-expanded',String(!expanded));
    nav.classList.toggle('open',!expanded);
    toggle.setAttribute('aria-label',expanded?'Ouvrir le menu':'Fermer le menu');
  });
  nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
    nav.classList.remove('open');toggle.setAttribute('aria-expanded','false');
  }));
  window.addEventListener('keydown',e=>{
    if(e.key==='Escape'){nav.classList.remove('open');toggle.setAttribute('aria-expanded','false');}
  });
}
document.querySelectorAll('form[data-confirm]').forEach(form=>{
  form.addEventListener('submit',e=>{
    if(!window.confirm(form.dataset.confirm||'Confirmer cette opération ?')) e.preventDefault();
  });
});
document.querySelectorAll('form[data-form="contact"]').forEach(form=>{
  form.addEventListener('submit',()=>{
    const button=form.querySelector('button[type="submit"]');
    if(button&&form.checkValidity()){
      button.disabled=true;button.textContent='Envoi en cours…';
    }
  });
});
const header=document.querySelector('.site-header');
if(header){
  const onScroll=()=>header.classList.toggle('is-scrolled',window.scrollY>8);
  onScroll();window.addEventListener('scroll',onScroll,{passive:true});
}
// Premier champ en erreur : focus automatique pour corriger vite.
const firstInvalid=document.querySelector('[aria-invalid="true"]');
if(firstInvalid){firstInvalid.focus({preventScroll:false});}
