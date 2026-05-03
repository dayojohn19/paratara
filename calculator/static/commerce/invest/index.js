console.log('Loaded JavaScript');




function calculate(mode){
    console.log('calculating..', mode);
    stock = document.querySelector("#stock").value;
    amount = document.querySelector("#amount").value;
    price = document.querySelector("#price").value;
    mode == 'buy'? buy() : mode == 'sell' ? sell () : alert("ERROR");
    function buy(){
        console.log('buying..',price,' at ',amount)
    }

    function sell(){
        console.log('selling..',price,' at ',amount)
    }
    result = fees_bdo(amount, mode, price);
    console.log('Result: ', result);
}


function sell(amount, price){
    try{
        price, cost = price;
        cost = price[1];
        if (cost == 0){
            console.log('cost is less than #########')
            price = price;
        } else {

            price = price[0]

        }
    }
    catch(err){
        price = price
    }

    console.log('Going to Calculate ', amount, price)
    amount_value = parseFloat(amount) * parseFloat(price);
    fee = calculate_fees(amount_value, 'sell')

    sell_total = parseFloat(amount_value) - parseFloat(fee); //total you get after selling
    try{
        if (parseFloat(sell_total) < parseFloat(cost) ){
            console.log('Price: ', price)
            price *= 1.002;
            price = [price, cost];
            console.log('added price, returning sell..')
            console.log('Credit: ', sell_total, 'Cost: ' , cost)

            sell(amount, price, fee);
        } else {
            console.log('FINAL Price: ', price);
            console.log('Total Fee: ', fee)
            console.log('Credit: ', sell_total, 'Cost: ' , cost)
            sell_stock(sell_total , price , amount);
        }

        
    }
    catch(err){
        console.log('Error near line 53')
        sell_stock(amount_value , fee);
    }
    
    return sell_total
}

// configure fees here
    function calculate_fees(amount, mode){
        console.log('\n........ CALCULATING FEES ....... \n');
        fee = 0
        security = parseFloat(amount) * 0.0001;
        fee += parseFloat(security);
        console.log('fees security: ', security);
        
        broker = parseFloat(amount) * 0.0025;
        fee += parseFloat(broker)
        console.log('fees broker: ',broker);

        vat = parseFloat(broker) * 0.12;
        fee += parseFloat(vat)
        console.log('fees vat: ',vat);
        if (mode == 'sell'){
            sale = parseFloat(amount) * 0.0060;
            fee += parseFloat(sale)
        }
        console.log('Total FEE: ', fee, mode)
        return fee
    }  
// -------
function fees_bdo(amount, mode, price){
    if (mode == 'sell') {
        sell(amount, price);
    }
    if (mode == 'buy'){
        fee = calculate_fees(amount, mode)
        buy_total = parseFloat(amount) + parseFloat(fee);
        buy_stock(amount, price, fee);  
        console.log('fee Bought',buy_total);
        return buy_total
    }
    return total 
}

function buy_stock(amount, price, fee){
    actual = parseFloat(amount) - parseFloat(fee);
    console.log('Actual: ',actual);
    console.log('Amount: ', amount);
    console.log('Fee: ', fee);

    total = parseFloat(actual) / parseFloat(price);
    total = Math.floor(total)
    remaining = parseFloat(amount) - parseFloat(actual);
    remaining = remaining.toFixed(2);
    console.log('You can buy : ', total);
    console.log('For ', actual)

    document.querySelector("#result").value = total;
    document.querySelector("#result_for").value = actual;
    document.querySelector("#remaining").value = remaining;
// --------- sell
    function sell_position(total , actual ){
        quantity = total; // total is the quantity
        cost = actual;  // actual is the total cost including fees
        price = parseFloat(cost) / parseFloat(quantity); //getting the acerage price
        console.log('You bought at Average Price: ', price);
        // amount = cost;
        price_cost = [price, actual]
        sell(quantity,  price_cost, fee)
    }
    sell_position(total, actual);
}

function sell_stock(sell_total, price, amount){

    console.log('You will get: ', sell_total);

    document.querySelector("#sell_amount").value = amount;
    document.querySelector("#sell_price").value = price.toFixed(3);
    document.querySelector("#sell_get").value = sell_total.toFixed(0);
// ----getting the profit
    cost = document.querySelector("#result_for").value;
    profit = parseFloat(sell_total) - parseFloat(cost);
    document.querySelector("#profit").value = profit.toFixed(0);
}




function calculate_profit(mode){
    price = document.querySelector("#sell_price")
    price_value = price.value;

    if (parseInt(price_value) == 0){
        return alert('Cannot be done');
    }

    increment = document.querySelector("#increment");
    increment_value = parseFloat(increment.value) / 100;

    amount = document.querySelector("#sell_amount").value;

    cost = document.querySelector("#result_for").value;
    if (mode == 'add'){
        increment_value += 0.00035
        price_value = (parseFloat(price_value) * parseFloat(increment_value))+ parseFloat(price_value)
    }
    if (mode == 'subtract'){
        increment_value -= 0.00035
        price_value = (parseFloat(price_value) * parseFloat(increment_value))+ parseFloat(price_value)
    }
    if ( increment_value < 0 ) {
        return alert('Cannot sell on Negative');
    }

    incremented_price = document.querySelector("#incremented_price");
    incremented_price.value = price_value.toFixed(3);
    increment.value = (increment_value * 100).toFixed(3) ;

    console.log('going to sell ' , amount, price_value);
    console.log('COST : COST : ', cost)
    price_cost = [price_value, cost]
    console.log('COSTCOST: ',price_cost)
    sell(amount, price_cost)


}

function calculate_sell(value){
    quantity = document.querySelector("#sell_amount").value;
    price = value;
    cost = document.querySelector("#result_for").value;
    amount = parseFloat(quantity) //* parseFloat(price);
    price_cost = [parseFloat(price), parseFloat(cost)]
    console.log(price_cost);
    console.log(amount);
    sell(amount, price_cost);
}