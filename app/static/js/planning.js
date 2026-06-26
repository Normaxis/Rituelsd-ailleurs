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

function styleAvailabilityBlocks(){
  document.querySelectorAll('.appointment-card-premium.block-present').forEach(function(block){
    block.style.pointerEvents='none';
    block.style.zIndex='0';
    block.style.left='0';
    block.style.right='0';
    block.style.borderRadius='0';
    block.style.border='0';
    block.style.background='rgba(82,190,119,.16)';
    block.style.color='transparent';
    block.style.boxShadow='none';
    block.style.padding='0';
    block.querySelectorAll('*').forEach(function(child){child.style.display='none';});
  });
}

function slotIsInAvailability(cell){
  if(cell.dataset.resourceType!=='user')return true;
  const track=cell.closest('.premium-track');
  if(!track)return false;
  const availabilityBlocks=track.querySelectorAll('.appointment-card-premium.block-present');
  if(!availabilityBlocks.length)return false;
  const rect=cell.getBoundingClientRect();
  const middleY=(rect.top+rect.bottom)/2;
  return Array.from(availabilityBlocks).some(function(block){
    const blockRect=block.getBoundingClientRect();
    return middleY>=blockRect.top&&middleY<=blockRect.bottom;
  });
}

document.addEventListener('DOMContentLoaded',function(){
  const board=document.querySelector('.planning-premium');
  if(!board)return;
  styleAvailabilityBlocks();
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