function UpdateResortData(resortData) {
    document.querySelector("#resort_headerImage").setAttribute('style',`background-image:url(${resortData.resort_headerImage})`)
    document.querySelector("#resort_RealName").innerHTML = resortData.resort_RealName;
    document.querySelector("#resort_address").innerHTML = resortData.resort_address;
    document.querySelector("#resort_description").innerHTML = resortData.resort_description;
    document.querySelector("#resort_promotional_video").setAttribute('src', `/resorts/static/resorts/videoclip/videotest.mov`);

    
    CreateCarousels(resortData)
}


function CreateCarousels(resortData) {
    console.log()
    accomodation_container = document.querySelector("#resort_Accomodations")
    accomodation_data = resortData.resort_Accomodations
    activity_container = document.querySelector("#resort_Activities")
    activity_data = resortData.resort_Activities

    tour_container = document.querySelector("#resort_Tour")
    tour_data = resortData.resort_Tour

    CreateEachPackages(accomodation_data,accomodation_container)
    CreateEachPackages(activity_data,activity_container)
    CreateEachPackages(tour_data,tour_container)

    function CreateEachPackages(resort_data,data_container){
        console.log('DATA \n\n\n')
        console.log(resort_data)
        // data = JSON.parse(data)
        // console.log('PARSED: ',data)
        resort_data.forEach(package => {
            CarouselMainContainerDetails = document.createElement('details');
            CarouselMainContainerDetails.className = 'package-summary'
            CarouselMainContainerDetails.open = true
        
            CarouselSummary = document.createElement('summary') 
            CarouselSummary.className='sub-package-summary badge'
    
            CarouselTitle = document.createElement('span')
            CarouselTitle.className='sub-package-title';
            CarouselTitle.textContent=package.package_title;
            CarouselSummary.append(CarouselTitle)
            CarouselMainContainerDetails.appendChild(CarouselSummary)
            data_container.append(CarouselMainContainerDetails)

            package.package_subpackage.forEach(subpackage =>{


                package_item = document.createElement('div')
                    package_item.className = 'room-item red-red-white'

                package_details = document.createElement('details')
                    package_details.open = true
                package_summary = document.createElement('summary')
                package_summary.id = 'package-'+subpackage.package_id
                package_summary.textContent = subpackage.package_name
                package_details.append(package_summary)
                package_description = document.createElement('p')
                package_description.textContent = subpackage.package_description
                package_details.append(package_description)
                package_information = document.createElement('span')
                package_information.className = 'sub-information'
                package_information.textContent = subpackage.package_information
                package_details.append(package_information)
                package_book_button = document.createElement('button')
                package_book_button.className='button-book'
                // package_book_button.setAttribute('onclick',alert('Make: ',subpackage.package_name))
                package_book_button.textContent = 'Book'
                package_details.append(package_book_button)




                package_item.append(package_details)
                CarouselMainContainerDetails.append(package_item)
                

                package_carousel = document.createElement('div')
                package_carousel.id = 'carousel_image-'+package.resortpackage_id+subpackage.package_id
                package_carousel.className = 'carousel slide'
                package_carousel.setAttribute("data-bs-ride", true)

                CarouselMainContainerDetails.append(package_carousel)

                
                
                // Not yet appended
                package_inner_carousel = document.createElement('div')
                package_inner_carousel.className = 'carousel-inner'
                package_carousel.append(package_inner_carousel)
                subpackage.package_image.forEach(function callback(eachImage, index) {
                    carousel_image_container = document.createElement('div')
                    if(index==0){
                        carousel_image_container.className = 'carousel-item active'
                    } else {
                        carousel_image_container.className = 'carousel-item'
                    }
                    carousel_image_item = document.createElement('img')
                    carousel_image_item.setAttribute('src',eachImage)
                    
                    carousel_image_container.append(carousel_image_item)
                    package_inner_carousel.append(carousel_image_container)
                    // CarouselMainContainerDetails.append(package_inner_carousel)
                });
                    button_prev = document.createElement('button')
                    button_prev.setAttribute('data-bs-target','#carousel_image-'+package.resortpackage_id+subpackage.package_id)
                    button_prev.className='carousel-control-prev',
                    button_prev.setAttribute('type','button')
                    button_prev.setAttribute('data-bs-slide',"prev")

                    button_prev_icon = document.createElement('span')
                    button_prev_icon.setAttribute('data-bs-target','#carousel_image-'+package.resortpackage_id+subpackage.package_id)
                    button_prev_icon.className = 'carousel-control-prev-icon'
                    button_prev_icon.setAttribute('aria-hidden',true)
                    button_prev.append(button_prev_icon)
                    button_previous = document.createElement('span')
                    button_previous.className = 'visually-hidden'
                    button_previous.textContent = 'Previous'
                    button_prev.append(button_previous)
                    package_inner_carousel.append(button_prev)
                    // 
                    // 
                    button_ne = document.createElement('button')
                    button_ne.setAttribute('data-bs-target','#carousel_image-'+package.resortpackage_id+subpackage.package_id)
                    button_ne.className='carousel-control-next',
                    button_ne.setAttribute('type','button')
                    button_ne.setAttribute('data-bs-slide',"next")

                    button_ne_icon = document.createElement('span')
                    button_ne_icon.setAttribute('data-bs-target','#carousel_image-'+package.resortpackage_id+subpackage.package_id)
                    button_ne_icon.className = 'carousel-control-next-icon'
                    button_ne_icon.setAttribute('aria-hidden',true)
                    button_ne.append(button_ne_icon)
                    button_next = document.createElement('span')
                    button_next.className = 'visually-hidden'
                    button_next.textContent = 'Previous'
                    button_prev.append(button_next)
                    package_inner_carousel.append(button_ne)

                
                // CarouselMainContainerDetails.append(package_inner_carousel)

            })

        });

    }


}
  





// function createTourPackageContainer(tourdata) {
//     document.createElement('')
// }
// function createTourPackageContainer(tourdata) {
//         tourdata.forEach((tour_element) => {
//         for (i = 0; i != tour_element.package_subpackage.length; i++){
//             console.log(i)
//             sub_package_item = tour_element.package_subpackage[i]
//             TourSubContainer = `
//                     <div class="carousel-inner">
//                       <div id="sub-package-img-${sub_package_item.package_id}" class="carousel-item">
//                       ${sub_package_item.package_image.forEach(element => {
//                         return `<img id="sub-image" src=${element}  class="d-block w-100" alt="..." id="{{images.id}}}}-{{acc.id}}-{{sub.id}}-Slides" onclick="PutToBlockContainer(id)" />`
//                       })}
//                         <img src="/resorts/static/resorts/pictureclip/picturetest.png" class="d-block w-100" alt="..." id="{{images.id}}}}-{{acc.id}}-{{sub.id}}-Slides" onclick="PutToBlockContainer(id)" />
//                       </div>
//                     </div>
//                     <span>
//                       <span id="sub-package-name-${sub_package_item.package_id}>
//                         ${sub_package_item.package_name}
//                       </span>
//                       <p>${sub_package_item.package_description}</p>
//                       <p>${sub_package_item.package_information}</p>
//                       <button class="button-book" onclick="bookNow('Booking ${sub_package_item.package_name}\n ₱${sub_package_item.package_price}')">Book</button>
//                     </span>

//             `
//         }

    
//         TourContainer = `
//                 <details open class="package-summary ">
//                 <summary class="sub-package-summary badge" >
//                     <span id="package-title" class=""> ${tour_element.package_title} </span>
//                 </summary>
//                     <li style="margin-top: 3rem">
//                     <div id="carousel-tour-package-${tour_element.resortpackage_id}" class="carousel slide" data-bs-ride="carousel">
//                     ${TourSubContainer}
//                     </div>
//                     <hr>
//                     </li>
//                 </details>`
//         })

//     console.log(typeof (CreatedTourContainer));
//     return TourContainer
        
// }