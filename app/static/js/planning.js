let dragged=null;

function isMobilePlanner(){
  return window.matchMedia('(max-width:1200px)').matches;
}

function openDrawer(){
  const board=document.querySelector('.planning-premium');
  const drawer=document.getElementById('appointmentDrawer');
  const backdrop=document.getElementById('drawerBackdrop');
  if(board)board.classList.remove('panel-collapsed');
  if(drawer)drawer.classList.add('open');
  if(backdrop&&isMobilePlanner())backdrop.classList.add('open');
}

function closeDrawer(){
  const board=document.querySelector('.planning-premium');
  const drawer=document.getElementById('appointmentDrawer');
  const backdrop=document.getElementById('drawerBackdrop');
  if(board)board.classList.add('panel-collapsed');
  if(isMobilePlanner()&&drawer)drawer.classList.remove('open');
  if(backdrop)backdrop.classList.remove('open');
}

function markAvailableSlots(){
  document.querySelectorAll('.premium-track').forEach(function(track){
    const presentBlocks=Array.from(track.querySelectorAll('.appointment-card-premium.block-present'));
    const slotCells=Array.from(track.querySelectorAll('.slot-drop'));
    const resource=track.closest('.premium-resource');
    const hasUserResource=resource&&resource.dataset.resourceType==='user';

    presentBlocks.forEach(function(block){
      block.style.display='';
      block.style.pointerEvents='none';
      block.style.opacity='0';
      block.style.zIndex='0';
    });

    slotCells.forEach(function(cell){
      if(!hasUserResource){
        cell.dataset.available='1';
        return;
      }
      const rect=cell.getBoundingClientRect();
      const middleY=(rect.top+rect.bottom)/2;
      const available=presentBlocks.some(function(block){
        const blockRect=block.getBoundingClientRect();
        return middleY>=blockRect.top&&middleY<=blockRect.bottom;
      });
      cell.dataset.available=available?'1':'0';
      cell.classList.toggle('is-available',available);
      cell.classList.toggle('is-unavailable',!available);
      if(available){
        cell.style.background='rgba(82,190,119,.16)';
        cell.style.borderBottom='1px solid rgba(82,190,119,.22)';
      }else{
        cell.style.background='transparent';
        cell.style.borderBottom='';
      }
    });

    presentBlocks.forEach(function(block){
      block.style.display='none';
    });
  });
}

function refreshAvailability(){
  requestAnimationFrame(function(){
    markAvailableSlots();
    setTimeout(markAvailableSlots,80);
  });
}

function slotIsInAvailability(cell){
  if(cell.dataset.resourceType!=='user')return true;
  return cell.dataset.available==='1';
}

document.addEventListener('DOMContentLoaded',function(){
  const board=document.querySelector('.planning-premium');
  if(!board)return;
  refreshAvailability();
  window.addEventListener('load',refreshAvailability);
  window.addEventListener('resize',refreshAvailability);
  const createDate=document.getElementById('createDate');
  const createTime=document.getElementById('createTime');
  const createUser=document.getElementById('createUser');
  const createCabin=document.getElementById('createCabin');
  const selectedSlotLabel=document.getElementById('selectedSlotLabel');
  const drawerClose=document.getElementById('drawerClose');
  const drawerBackdrop=document.getElementById('drawerBackdrop');
  const railOpen=document.getElementById('drawerOpenRail');

  document.querySelectorAll('.new-rdv-trigger').forEach(function(btn){btn.addEventListener('click',openDrawer);});
  if(railOpen)railOpen.addEventListener('click',openDrawer);
  if(drawerClose)drawerClose.addEventListener('click',closeDrawer);
  if(drawerBackdrop)drawerBackdrop.addEventListener('click',closeDrawer);

  document.addEventListener('keydown',function(e){
    if(e.key==='Escape')closeDrawer();
  });

  document.addEventListener('dragstart',function(e){
    const item=e.target.closest('[data-event-id]');
    if(!item)return;
    if(item.classList.contains('block-present'))return;
    dragged={event_type:item.dataset.eventType,event_id:item.dataset.eventId};
    item.classList.add('dragging');
  });

  document.addEventListener('dragend',function(e){
    const item=e.target.closest('[data-event-id]');
    if(item)item.classList.remove('dragging');
  });

  document.querySelectorAll('.slot-drop').forEach(function(cell){
    cell.addEventListener('click',function(){
      const resourceType=cell.dataset.resourceType;
      const resourceId=cell.dataset.resourceId;
      const slotTime=cell.dataset.time;
      if(!slotIsInAvailability(cell)){
        alert('Cette praticienne n est pas disponible sur ce creneau. Cliquez dans une zone verte.');
        return;
      }
      if(createDate)createDate.value=board.dataset.date;
      if(createTime)createTime.value=slotTime;
      if(resourceType==='user'&&createUser)createUser.value=resourceId;
      if(resourceType==='cabin'&&createCabin)createCabin.value=resourceId;
      if(selectedSlotLabel)selectedSlotLabel.textContent=board.dataset.date+' · '+slotTime;
      openDrawer();
    });

    cell.addEventListener('dragover',function(e){
      e.preventDefault();
      if(slotIsInAvailability(cell))cell.classList.add('drop-hover');
    });
    cell.addEventListener('dragleave',function(){cell.classList.remove('drop-hover');});
    cell.addEventListener('drop',function(e){
      e.preventDefault();cell.classList.remove('drop-hover');
      if(!dragged)return;
      if(!slotIsInAvailability(cell)){
        alert('Impossible : la praticienne n est pas disponible sur ce creneau.');
        return;
      }
      const payload={event_type:dragged.event_type,event_id:dragged.event_id,resource_type:cell.dataset.resourceType,resource_id:cell.dataset.resourceId,time:cell.dataset.time,date:board.dataset.date};
      fetch('/admin/planning/api/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
        .then(function(r){return r.json().then(function(j){return {ok:r.ok,body:j};});})
        .then(function(res){if(res.ok&&res.body.ok){window.location.reload();}else{alert(res.body.message||'Deplacement impossible');}})
        .catch(function(){alert('Erreur reseau');});
    });
  });
});