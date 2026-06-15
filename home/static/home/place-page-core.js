(function(){let config=window.placePageConfig||{},runWhenReady=window.placePageReady;window.ensurePlaceSubCardStyles=function(){if(document.getElementById(`pcs`))return;let style=document.createElement(`style`);style.id=`pcs`,style.textContent=`
        .pcg {
          display: flex;
          flex-wrap: wrap;
          gap:0.2rem;
          margin: 1.2rem 0 0 0;
        }
        .pc {
          background: #fff;
          overflow: hidden;
          width: 220px;
          display: flex;
          flex-direction: column;
          align-items: stretch;
        }
        button.pc,
        .pic {
          border: 0;
          padding: 0;
          color: inherit;
          cursor: pointer;
          font: inherit;
          text-align: left;
        }
        .pic:focus-visible {
          outline: 2px solid #667eea;
          outline-offset: 2px;
        }
        .ag {
          margin-bottom: 1.35rem;
        }
        .agt {
          color: #222;
          font-size: 1.05rem;
          font-weight: 700;
          line-height: 1.35;
          margin: 0;
        }
        .pci {
          width: 100%;
          height: 200px;
          object-fit: cover;
          display: block;
        }
        .pcb {
          padding: 0.8rem 1rem 1.1rem 1rem;
          flex: 1 1 auto;
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
          align-items: flex-start;
        }
        .pct {
          font-size: 0.92rem;
          font-weight: 650;
          line-height: 1.35;
          margin-bottom: 0.35rem;
          color: #222;
        }
        .pcp {
          font-size: 0.88rem;
          line-height: 1.35;
          color: var(--accent);
          font-weight: 650;
        }
        .pcr {
          margin-top: 0.35rem;
          color: #64748b;
          font-size: 0.78rem;
          line-height: 1.3;
          font-weight: 650;
        }
        .rs {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          color: #cbd5e1;
          line-height: 1;
        }
        .rss {
          color: #cbd5e1;
        }
        .rss.ia {
          color: #f59e0b;
        }
        .rsc {
          color: #64748b;
          font-size: 0.82rem;
          line-height: 1;
          margin-left: 4px;
        }
        .pima {
          min-height: 1.35rem;
        }
        .pima .rs {
          font-size: 1.1rem;
        }
        .prv {
          border-top: 1px solid rgba(148, 163, 184, 0.35);
          margin-top: 8px;
          padding-top: 14px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .prv[hidden] {
          display: none;
        }
        .prvs {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          flex-wrap: wrap;
          color: var(--text);
          font-size: 0.95rem;
          font-weight: 700;
        }
        .prvb {
          border: 1px solid rgba(102, 126, 234, 0.28);
          background: #fff;
          color: var(--accent);
          padding: 7px 10px;
          font: inherit;
          font-size: 0.88rem;
          font-weight: 700;
          cursor: pointer;
        }
        .prf {
          display: grid;
          gap: 8px;
        }
        .prfr {
          display: grid;
          grid-template-columns: minmax(90px, 120px) minmax(0, 1fr);
          gap: 8px;
        }
        .prf input,
        .prf select,
        .prf textarea {
          border: 1px solid rgba(148, 163, 184, 0.45);
          padding: 8px 10px;
          font: inherit;
          color: var(--text);
          background: #fff;
        }
        .prf textarea {
          resize: vertical;
          min-height: 64px;
        }
        .prf button {
          justify-self: start;
          border: 0;
          background: var(--accent);
          color: #fff;
          padding: 8px 12px;
          font: inherit;
          font-weight: 750;
          cursor: pointer;
        }
        .psr {
          display: flex;
          align-items: center;
          gap: 4px;
          flex-wrap: wrap;
        }
        .prf .psrs {
          border: 0;
          background: transparent;
          color: #cbd5e1;
          padding: 0 2px;
          font-size: 1.85rem;
          line-height: 1;
          cursor: pointer;
        }
        .prf .psrs.ia {
          color: #f59e0b;
        }
        .prf .psrs:focus-visible {
          outline: 2px solid var(--accent);
          outline-offset: 2px;
        }
        .psrl {
          color: #64748b;
          font-size: 0.88rem;
          line-height: 1.35;
          margin-left: 6px;
        }
        .prst {
          min-height: 1.2em;
          color: #64748b;
          font-size: 0.88rem;
          line-height: 1.35;
        }
        .prl {
          display: grid;
          gap: 8px;
        }
        .prw {
          padding: 10px;
        }
        .prvm {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          color: var(--text);
          font-size: 0.88rem;
          font-weight: 700;
        }
        .prvd {
          color: #64748b;
          font-size: 0.8rem;
          line-height: 1.35;
          margin-top: 4px;
        }
        .prvc {
          margin: 6px 0 0;
          color: var(--text-muted);
          font-size: 0.9rem;
          line-height: 1.45;
          white-space: pre-line;
        }
        @media (max-width: 600px) {
          .pc {
            width: calc(50% - 0.1rem);
          }
          .pci {
            height: 120px;
          }
          .prfr {
            grid-template-columns: 1fr;
          }
        }
      `,document.head.appendChild(style)};let hEsc={"&":`&amp;`,"<":`&lt;`,">":`&gt;`,'"':`&quot;`,"'":`&#39;`},ims={images:[],index:0,item:null},items=[],rev={packageId:``,commentsLoaded:!1,loading:!1,nextOffset:0,hasMore:!1},canReview=!!config.canReview,loginUrl=config.loginUrl||`/userProfile/login/`;function fv(){for(let i=0;i<arguments.length;i+=1){let value=arguments[i];if(value!=null&&String(value).trim()!==``)return value}return``}function escapeHtml(value){return String(value||``).replace(/[&<>"']/g,function(char){return hEsc[char]})}function normImgs(value){return Array.isArray(value)?value.map(function(item){return typeof item==`string`?item:item&&(item.urlField||item.url||item.imageURL||item.src||``)}).filter(function(url){return!!url}):typeof value==`string`&&value.trim()!==``?[value]:[]}function numVal(value,fallback){let parsed=Number(value);return Number.isFinite(parsed)?parsed:fallback}function starsHtml(average,count){let ratingCount=numVal(count,0);if(!ratingCount)return``;let ratingValue=Math.max(0,Math.min(5,Math.round(numVal(average,0)))),stars=``;for(let i=1;i<=5;i+=1)stars+=`<span class="rss`+(i<=ratingValue?` ia`:``)+`">&#9733;</span>`;return`<span class="rs" aria-label="`+numVal(average,0).toFixed(1)+` out of 5">`+stars+`<span class="rsc">(`+ratingCount+`)</span></span>`}function ratingStarsHtml(rating){let ratingValue=Math.max(0,Math.min(5,Math.round(numVal(rating,0)))),stars=``;for(let i=1;i<=5;i+=1)stars+=`<span class="rss`+(i<=ratingValue?` ia`:``)+`">&#9733;</span>`;return`<span class="rs" aria-label="`+ratingValue+` out of 5">`+stars+`</span>`}function readableReviewTime(value){if(!value)return``;let date=new Date(value);return Number.isNaN(date.getTime())?``:date.toLocaleString(`en-US`,{month:`long`,day:`numeric`,year:`numeric`,hour:`numeric`,minute:`2-digit`})}function normItem(rawItem,fallbackTitle){let item=rawItem||{},images=normImgs(item.images);images.length||(images=normImgs(item.package_image)),images.length||(images=normImgs(item.imageURL)),images.length||(images=normImgs(item.resort_Gallery));let packageId=fv(item.package_id,item.packageId);return Object.assign({},item,{packageId,title:fv(item.title,item.package_title,item.package_name,item.PackageTitle,item.name,fallbackTitle,`Item`),description:fv(item.description,item.package_description),information:fv(item.information,item.package_information),price:fv(item.price,item.package_price),images,resortLink:fv(item.resortLink,item.resortURL,item.resort_websiteURL),resortName:fv(item.resortName,item.resort_RealName,item.resort_name),websiteURL:fv(item.websiteURL,item.website,item.package_website),ratingAverage:numVal(fv(item.package_rating_average,item.rating_average,item.ratingAverage),0),ratingCount:numVal(fv(item.package_rating_count,item.rating_count,item.ratingCount),0)})}function priceText(value,emptyLabel){let label=emptyLabel===void 0?`Price not listed`:emptyLabel;if(value==null||String(value).trim()===``||String(value)===`0`)return label;let numVal=Number(value);if(Number.isFinite(numVal))return`₱`+numVal.toLocaleString();let textValue=String(value).trim();return textValue.indexOf(`₱`)===0?textValue:`₱`+textValue}function setTxt(id,value){let element=document.getElementById(id);return element&&(element.textContent=value||``),element}function setModalImg(nextIndex){let image=document.getElementById(`piI`),empty=document.getElementById(`piE`),counter=document.getElementById(`piC`),prev=document.getElementById(`piP`),next=document.getElementById(`piN`),images=ims.images||[];if(!(!image||!empty)){if(!images.length){image.removeAttribute(`src`),image.style.display=`none`,empty.style.display=`flex`,counter&&(counter.textContent=`0 / 0`),prev&&(prev.hidden=!0),next&&(next.hidden=!0);return}ims.index=(nextIndex+images.length)%images.length,image.src=images[ims.index],image.alt=ims.item?ims.item.title:`Item photo`,image.style.display=`block`,empty.style.display=`none`,counter&&(counter.textContent=ims.index+1+` / `+images.length),prev&&(prev.hidden=images.length<=1),next&&(next.hidden=images.length<=1)}}window.placeItemModalState=ims,window.placeItemDetails=items,window.placeEscapeHtml=escapeHtml,window.placeNormalizeImages=normImgs,window.placeFormatPrice=priceText,window.placePageSize=10,window.placeGetPaginatedResults=function(payload,legacyNestedKey){if(payload&&Array.isArray(payload.results))return payload.results;let rows=[];return(Array.isArray(payload)?payload:[]).forEach(function(item){item&&legacyNestedKey&&Array.isArray(item[legacyNestedKey])?rows.push.apply(rows,item[legacyNestedKey]):item&&rows.push(item)}),rows},window.placeSetLoadMoreButton=function(containerId,hasNext,isLoading,onClick){let container=document.getElementById(containerId);if(!container)return;if(!hasNext&&!isLoading){container.innerHTML=``,container.hidden=!0;return}container.hidden=!1,container.innerHTML=`<button type="button" class="button button--ghost place-load-more-btn">`+(isLoading?`Loading...`:`Load more`)+`</button>`;let button=container.querySelector(`button`);button&&(button.disabled=!!isLoading,isLoading||button.addEventListener(`click`,onClick))},window.registerPlaceItemDetail=function(rawItem,fallbackTitle){let item=normItem(rawItem,fallbackTitle);return items.push(item),items.length-1},window.placeBuildItemCard=function(rawItem,fallbackTitle){let item=normItem(rawItem,fallbackTitle),index=window.registerPlaceItemDetail(item,fallbackTitle),imageSrc=item.images[0]||``,ratingHtml=item.packageId?starsHtml(item.ratingAverage,item.ratingCount):``,imageTag=imageSrc?`<img src="${escapeHtml(imageSrc)}" alt="${escapeHtml(item.title)}" class="pci"${window.placeLazyImageAttrs||``} />`:``;return`
        <button type="button" class="pc pic jpic" data-pi="${index}" aria-label="View ${escapeHtml(item.title)}">
          ${imageTag}
          <span class="pcb">
            <span class="pct">${escapeHtml(item.title)}</span>
            <span class="pcp">${escapeHtml(priceText(item.price))}</span>
            ${ratingHtml?`<span class="pcr">${ratingHtml}</span>`:``}
          </span>
        </button>
      `};function csrfToken(){return typeof getCookie==`function`&&getCookie(`csrftoken`)||``}function setReviewStatus(message,isError){let status=document.getElementById(`prS`);status&&(status.textContent=message||``,status.style.color=isError?`#b91c1c`:`#64748b`)}function setReviewSummary(item,average,count){item&&(item.ratingAverage=numVal(average,0),item.ratingCount=numVal(count,0));let summary=document.getElementById(`prY`);summary&&(summary.innerHTML=starsHtml(item?item.ratingAverage:average,item?item.ratingCount:count)||``);let modalRating=document.getElementById(`piA`);if(modalRating){let ratingHtml=starsHtml(item?item.ratingAverage:average,item?item.ratingCount:count);modalRating.innerHTML=ratingHtml,modalRating.hidden=!ratingHtml}}function setStars(value){let rating=Math.max(1,Math.min(5,numVal(value,0))),ratingField=document.getElementById(`prV`),label=document.getElementById(`psL`),stars=document.querySelectorAll(`.psrs`);ratingField&&(ratingField.value=rating?String(rating):``),label&&(label.textContent=rating?rating+`/5 selected`:`Choose rating`),stars.forEach(function(star){let starRating=numVal(star.getAttribute(`data-rating`),0),active=rating&&starRating<=rating;star.classList.toggle(`ia`,!!active),star.setAttribute(`aria-pressed`,active?`true`:`false`)})}function renderReviewPanel(item){let panel=document.getElementById(`prP`);if(!panel)return;let packageId=item&&item.packageId?String(item.packageId):``;if(rev.packageId=packageId,rev.commentsLoaded=!1,rev.loading=!1,rev.nextOffset=0,rev.hasMore=!1,!packageId){panel.hidden=!0,panel.innerHTML=``;return}let reviewForm=canReview?`
          <form id="prF" class="prf">
            <div class="prfr">
              <div class="psr" role="radiogroup" aria-label="Rating">
                <input type="hidden" name="rating" id="prV" required />
                <button type="button" class="psrs" data-rating="1" aria-label="1 out of 5" aria-pressed="false">&#9733;</button>
                <button type="button" class="psrs" data-rating="2" aria-label="2 out of 5" aria-pressed="false">&#9733;</button>
                <button type="button" class="psrs" data-rating="3" aria-label="3 out of 5" aria-pressed="false">&#9733;</button>
                <button type="button" class="psrs" data-rating="4" aria-label="4 out of 5" aria-pressed="false">&#9733;</button>
                <button type="button" class="psrs" data-rating="5" aria-label="5 out of 5" aria-pressed="false">&#9733;</button>
                <span id="psL" class="psrl">Choose rating</span>
              </div>
              <textarea name="comment" maxlength="800" placeholder="Comment optional"></textarea>
            </div>
            <button type="submit">Save rating</button>
          </form>
        `:`
          <button type="button" id="psT" class="prvb">Sign up to rate</button>
          <form id="psF" class="prf" hidden>
            <input name="contact" type="text" autocomplete="email" placeholder="Contact or email" required />
            <input name="username" type="text" autocomplete="username" placeholder="Username" required />
            <input name="password" type="password" autocomplete="new-password" placeholder="Password" minlength="6" required />
            <button type="submit">Create account</button>
            <p class="prst">Already have an account? <a href="${escapeHtml(loginUrl)}">Login</a>.</p>
          </form>
        `;panel.hidden=!1,panel.innerHTML=`
        <div class="prvs">
          <span id="prY">${starsHtml(item.ratingAverage,item.ratingCount)}</span>
          <button type="button" id="prB" class="prvb">Show comments</button>
        </div>
        ${reviewForm}
        <div id="prS" class="prst" aria-live="polite"></div>
        <div id="prL" class="prl" hidden></div>
        <button type="button" id="prM" class="prvb" hidden>Load more comments</button>
      `}function reviewHtml(review){let comment=review.comment?`<p class="prvc">${escapeHtml(review.comment)}</p>`:``,reviewTime=readableReviewTime(review.updated_at||review.created_at);return`
        <div class="prw">
          <div class="prvm">
            <span>${escapeHtml(review.user_name||`User`)}</span>
            <span>${ratingStarsHtml(review.rating)}</span>
          </div>
          ${reviewTime?`<div class="prvd">${escapeHtml(reviewTime)}</div>`:``}
          ${comment}
        </div>
      `}async function loadReviews(append){let packageId=rev.packageId;if(!packageId||rev.loading)return;let list=document.getElementById(`prL`),loadButton=document.getElementById(`prB`),moreButton=document.getElementById(`prM`),offset=append?rev.nextOffset:0;rev.loading=!0,list&&(list.hidden=!1,append||(list.innerHTML=`<div class="prst">Loading comments...</div>`)),loadButton&&(loadButton.disabled=!0,loadButton.textContent=`Loading...`),moreButton&&(moreButton.disabled=!0);try{let response=await fetch(`/est/package/${encodeURIComponent(packageId)}/reviews/?limit=5&offset=${offset}`,{headers:{Accept:`application/json`}});if(!response.ok)throw Error(`Failed to load comments`);let payload=await response.json();if(rev.packageId!==packageId)return;setReviewSummary(ims.item,payload.rating_average,payload.rating_count);let html=(Array.isArray(payload.reviews)?payload.reviews:[]).map(reviewHtml).join(``);list&&(append?list.insertAdjacentHTML(`beforeend`,html):list.innerHTML=html||`<div class="prst">No comments yet.</div>`),rev.commentsLoaded=!0,rev.hasMore=!!payload.has_more,rev.nextOffset=payload.next_offset||0,moreButton&&(moreButton.hidden=!rev.hasMore),setReviewStatus(``,!1)}catch{setReviewStatus(`Could not load comments right now.`,!0)}finally{rev.loading=!1,loadButton&&(loadButton.disabled=!1,loadButton.textContent=rev.commentsLoaded?`Refresh comments`:`Show comments`),moreButton&&(moreButton.disabled=!1)}}async function submitReview(form){let packageId=rev.packageId;if(!packageId||!form)return;let submitButton=form.querySelector(`button[type="submit"]`),ratingField=form.elements.rating,commentField=form.elements.comment,rating=ratingField?ratingField.value:``,comment=commentField?commentField.value:``;if(!rating){setReviewStatus(`Choose a rating from 1 to 5.`,!0);return}submitButton&&(submitButton.disabled=!0,submitButton.textContent=`Saving...`),setReviewStatus(``,!1);try{let response=await fetch(`/est/package/${encodeURIComponent(packageId)}/review/`,{method:`POST`,headers:{Accept:`application/json`,"Content-Type":`application/json`,"X-CSRFToken":csrfToken()},body:JSON.stringify({rating,comment})}),payload=(response.headers.get(`content-type`)||``).indexOf(`application/json`)===-1?null:await response.json();if(!response.ok||!payload||payload.success===!1)throw Error(payload&&payload.error?payload.error:`Could not save rating`);setReviewSummary(ims.item,payload.rating_average,payload.rating_count),setReviewStatus(`Rating saved.`,!1),rev.commentsLoaded&&await loadReviews(!1)}catch(error){setReviewStatus(error.message||`Could not save rating.`,!0)}finally{submitButton&&(submitButton.disabled=!1,submitButton.textContent=`Save rating`)}}async function submitSignup(form){if(!form)return;let submitButton=form.querySelector(`button[type="submit"]`),contact=(form.elements.contact?form.elements.contact.value:``).trim(),username=(form.elements.username?form.elements.username.value:``).trim(),password=form.elements.password?form.elements.password.value:``;if(!contact||!username||!password){setReviewStatus(`Fill in contact, username, and password.`,!0);return}submitButton&&(submitButton.disabled=!0,submitButton.textContent=`Creating...`),setReviewStatus(``,!1);try{let response=await fetch(`/userProfile/registerjson`,{method:`POST`,headers:{Accept:`application/json`,"Content-Type":`application/json`,"X-CSRFToken":csrfToken()},body:JSON.stringify({username,contact,password,passwordConfirmation:password,placeID:config.placeId})}),payload=await response.json().catch(function(){return null});if(!response.ok){let message=Array.isArray(payload)?payload[0]:payload&&(payload.error||payload.detail);throw Error(message||`Could not create account`)}canReview=!0,renderReviewPanel(ims.item),setReviewStatus(`Account ready. You can now rate this package.`,!1)}catch(error){setReviewStatus(error.message||`Could not create account.`,!0)}finally{submitButton&&(submitButton.disabled=!1,submitButton.textContent=`Create account`)}}window.openPlaceItemModal=function(itemOrIndex){let modal=document.getElementById(`piM`);if(!modal)return;let item=typeof itemOrIndex==`number`?items[itemOrIndex]:normItem(itemOrIndex||{});if(!item)return;window.ensurePlaceSubCardStyles&&window.ensurePlaceSubCardStyles(),ims.item=item,ims.images=item.images||[],ims.index=0,setTxt(`piT`,item.title),setTxt(`piR`,item.resortName),setTxt(`piPrice`,priceText(item.price)),setReviewSummary(item,item.ratingAverage,item.ratingCount);let description=[item.description,item.information].filter(Boolean).join(`

`),descriptionElement=setTxt(`piD`,description);descriptionElement&&(descriptionElement.hidden=!description);let link=document.getElementById(`piL`),linkUrl=item.resortLink||item.websiteURL||``;link&&linkUrl?(link.href=linkUrl,link.textContent=item.resortLink?`View Resort`:`Open Link`,link.hidden=!1):link&&(link.hidden=!0,link.removeAttribute(`href`)),setModalImg(0),renderReviewPanel(item),modal.classList.add(`is-open`),modal.setAttribute(`aria-hidden`,`false`),document.body.style.overflow=`hidden`},window.closePlaceItemModal=function(){let modal=document.getElementById(`piM`),image=document.getElementById(`piI`);image&&image.removeAttribute(`src`),modal&&(modal.classList.remove(`is-open`),modal.setAttribute(`aria-hidden`,`true`)),document.body.style.overflow=``},window.shiftPlaceItemModalImage=function(direction){setModalImg(ims.index+direction)},runWhenReady(function(){let closeButton=document.getElementById(`piX`),prevButton=document.getElementById(`piP`),nextButton=document.getElementById(`piN`);closeButton&&closeButton.addEventListener(`click`,window.closePlaceItemModal),prevButton&&prevButton.addEventListener(`click`,function(){window.shiftPlaceItemModalImage(-1)}),nextButton&&nextButton.addEventListener(`click`,function(){window.shiftPlaceItemModalImage(1)}),document.addEventListener(`click`,function(event){let card=event.target&&event.target.closest?event.target.closest(`.jpic`):null;if(!card)return;let index=Number(card.getAttribute(`data-pi`));Number.isFinite(index)&&window.openPlaceItemModal(index)}),document.addEventListener(`click`,function(event){if(event.target&&event.target.closest&&event.target.closest(`#prB`)){loadReviews(!1);return}if(event.target&&event.target.closest&&event.target.closest(`#psT`)){let signupForm=document.getElementById(`psF`);if(signupForm&&(signupForm.hidden=!signupForm.hidden,!signupForm.hidden)){let firstField=signupForm.querySelector(`input`);firstField&&firstField.focus()}return}let starButton=event.target&&event.target.closest?event.target.closest(`.psrs`):null;if(starButton){setStars(starButton.getAttribute(`data-rating`));return}event.target&&event.target.closest&&event.target.closest(`#prM`)&&loadReviews(!0)}),document.addEventListener(`submit`,function(event){!event.target||event.target.id!==`prF`&&event.target.id!==`psF`||(event.preventDefault(),event.target.id===`psF`?submitSignup(event.target):submitReview(event.target))}),document.addEventListener(`keydown`,function(event){let modal=document.getElementById(`piM`);!modal||!modal.classList.contains(`is-open`)||(event.key===`Escape`&&window.closePlaceItemModal(),event.key===`ArrowLeft`&&window.shiftPlaceItemModalImage(-1),event.key===`ArrowRight`&&window.shiftPlaceItemModalImage(1))})})})();function openBulletinImageModal(imageUrl){let modal=document.getElementById(`bulletinImageModal`),imageElement=document.getElementById(`bulletinModalImage`);!modal||!imageElement||(imageElement.src=imageUrl,modal.style.display=`block`,modal.setAttribute(`aria-hidden`,`false`))}function closeBulletinImageModal(){let modal=document.getElementById(`bulletinImageModal`),imageElement=document.getElementById(`bulletinModalImage`);imageElement&&(imageElement.src=``),modal&&(modal.style.display=`none`,modal.setAttribute(`aria-hidden`,`true`))}document.addEventListener(`click`,function(event){let link=event.target&&event.target.closest?event.target.closest(`a.bulletin-image-link`):null;if(!link)return;event.preventDefault();let imageUrl=link.getAttribute(`data-image-url`)||link.getAttribute(`href`);imageUrl&&openBulletinImageModal(imageUrl)}),window.placePageReady(function(){let button=document.getElementById(`bulletinPostButton`),form=document.getElementById(`bulletinPostForm`);!button||!form||button.addEventListener(`click`,function(){let isHidden=form.style.display===`none`||form.style.display===``;form.style.display=isHidden?`flex`:`none`})}),window.placePageReady(function(){let navToggle=document.getElementById(`placeNavToggle`),navMenu=document.getElementById(`placeNavMenu`);if(!navToggle||!navMenu)return;let navOpenMap=document.getElementById(`placeNavOpenMap`);function closeMenu(){navMenu.classList.remove(`is-open`),navToggle.setAttribute(`aria-expanded`,`false`)}navToggle.addEventListener(`click`,function(){let isOpen=navMenu.classList.toggle(`is-open`);navToggle.setAttribute(`aria-expanded`,isOpen?`true`:`false`)}),navMenu.addEventListener(`click`,function(event){event.target&&event.target.closest&&event.target.closest(`a, button`)&&closeMenu()}),navOpenMap&&navOpenMap.addEventListener(`click`,function(event){event&&event.preventDefault&&event.preventDefault();let existing=document.getElementById(`openMapBtn`);existing&&existing.click()}),document.addEventListener(`keydown`,function(event){event.key===`Escape`&&closeMenu()})});