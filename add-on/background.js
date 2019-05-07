/*
On startup, connect to the "ping_pong" app.
*/
var port = browser.runtime.connectNative("beeves_speech_server");
console.log(port)
console.log('woot')
/*
Listen for messages from the app.
*/
port.onMessage.addListener((response) => {
  console.log("Received: " + JSON.stringify(response));
});

/*
On a click on the browser action, send the app a message.
*/
browser.browserAction.onClicked.addListener(() => {
  console.log("Sending:  ping");
  port.postMessage("ping");
});
