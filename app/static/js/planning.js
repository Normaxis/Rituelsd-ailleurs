let dragged=null;

function openDrawer(){
  const drawer=document.getElementById('appointmentDrawer');
  const backdrop=document.getElementById('drawerBackdrop');
  if(drawer)drawer.classList.add('open');
  if(backdrop)backdrop.classList.add('open');
}

function closeDrawer(){
  const drawer=document.getElementById('appointmentDrawer');
  const backdrop=document.getElementById('drawerBackdrop');
  if(drawer)drawer.classList.remove('open');
  if(backdrop)backdrop.classList.remove('open');
}

document.addEventListener('DOMContentLoaded',function(){
  const board=document.querySelector('.planning-premium');
  if(!board)return;
  const createDate=document.getElementById('createDate');
  const createTime=document.getElementById('createTime');
  const createUser=document.getElementById('createUser');
  const createCabin=document.getElementById('createCabin');
  const selectedSlotLabel=document.getElementById('selectedSlotLabel');
  const drawerClose=document.getElementById('drawerClose');
  const drawerBackdrop=document.getElementById('drawerBackdrop');

  document.querySelectorAll('.new-rdv-trigger').forEach(function(btn){btn.addEventListener('click',openDrawer);});
  if(drawerClose)drawerClose.addEventListener('click',closeDrawer);
  if(drawerBackdrop)drawerBackdrop.addEventListener('click',closeDrawer);

  document.addEventListener('dragstart',function(e){
    const item=e.target.closest('[data-event-id]');
    if(!item)return;
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
      if(createDate)createDate.value=board.dataset.date;
      if(createTime)createTime.value=slotTime;
      if(resourceType==='user'&&createUser)createUser.value=resourceId;
      if(resourceType==='cabin'&&createCabin)createCabin.value=resourceId;
      if(selectedSlotLabel)selectedSlotLabel.textContent=board.dataset.date+' · '+slotTime;
      openDrawer();
    });

    cell.addEventListener('dragover',function(e){e.preventDefault();cell.classList.add('drop-hover');});
    cell.addEventListener('dragleave',function(){cell.classList.remove('drop-hover');});
    cell.addEventListener('drop',function(e){
      e.preventDefault();cell.classList.remove('drop-hover');
      if(!dragged)return;
      const payload={event_type:dragged.event_type,event_id:dragged.event_id,resource_type:cell.dataset.resourceType,resource_id:cell.dataset.resourceId,time:cell.dataset.time,date:board.dataset.date};
      fetch('/admin/planning/api/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
        .then(function(r){return r.json().then(function(j){return {ok:r.ok,body:j};});})
        .then(function(res){if(res.ok&&res.body.ok){window.location.reload();}else{alert(res.body.message||'Deplacement impossible');}})
        .catch(function(){alert('Erreur reseau');});
    });
  });
});