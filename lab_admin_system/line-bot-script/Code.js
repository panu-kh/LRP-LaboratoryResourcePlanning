// =================== 1. MASTER CONFIG ===================
// ✅ ดึงกุญแจลับจากระบบ Script Properties ของ Google 
const props = PropertiesService.getScriptProperties();
const CHANNEL_ACCESS_TOKEN = props.getProperty('LINE_TOKEN'); 
const SHEET_ID = props.getProperty('SHEET_ID'); 

const SHEET_BOOKINGS = 'Bookings';
const SHEET_USERS = 'Users';
const SHEET_MACHINES = 'Machines'; 
const SHEET_RATINGS = 'Ratings'; 
const SHEET_BLOCKED = 'BlockedSlots'; 

// 🎨 THEME CONFIG
const COLOR_THEME = {
  HEADER_BG: "#88304E",   
  BODY_BG: "#2C2C2C",      
  BUTTON_OK: "#88304E",    
  BUTTON_FULL: "#4F4F4F",  
  BUTTON_SELF: "#522546",  
  BUTTON_BLOCKED: "#666666", 
  TEXT_MAIN: "#FFFFFF",    
  TEXT_SUB: "#AAAAAA"      
};

// =================== 2. DYNAMIC CONFIG ===================
function getMachinesConfig() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_MACHINES);
  const data = sheet.getDataRange().getValues();
  let config = {};
  for (let i = 1; i < data.length; i++) {
    let status = data[i][5]; 
    if (status === 'Active') { 
      let wDays = [];
      if (data[i][6]) wDays = String(data[i][6]).split(',').map(d => parseInt(d.trim()));
      config[data[i][0]] = {
        floor: String(data[i][1]),
        slots: data[i][2].toString().split(',').map(s => s.trim()),
        color: data[i][3],
        image: data[i][4],
        warnDays: wDays,
        warnTime: String(data[i][7]).trim(),
        warnMsg: String(data[i][8]).trim().replace(/\\n/g, '\n'),
        warnCol: String(data[i][9]).trim() || "#FF5555"
      };
    }
  }
  return config;
}

function getBlockedSlotsConfig() {
  let config = {};
  try {
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BLOCKED);
    if (!sheet) return config;
    const data = sheet.getDataRange().getValues();

    for (let i = 1; i < data.length; i++) {
      if (data[i][4] === 'Active') { 
        let machine = String(data[i][0]).trim(); 
        let dateObj = data[i][1]; 
        let dateStr = (dateObj instanceof Date) ? Utilities.formatDate(dateObj, Session.getScriptTimeZone(), "yyyy-MM-dd") : String(dateObj).trim();
        let slots = String(data[i][2]).split(',').map(s => s.trim()); 
        let msg = String(data[i][3]).trim() || "ปิด / Closed"; 

        if (!config[machine]) config[machine] = {};
        if (!config[machine][dateStr]) config[machine][dateStr] = {};

        slots.forEach(s => {
          config[machine][dateStr][s] = msg;
        });
      }
    }
  } catch (e) {
    console.log("Error reading BlockedSlots: " + e);
  }
  return config;
}

// =================== 3. WEB APP ROUTING ===================
function doGet(e) {
  if (e.parameter && e.parameter.page === 'timeline') {
    return HtmlService.createHtmlOutputFromFile('timeline_view')
        .setTitle('Lab Timeline (6 Days)')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }
  return HtmlService.createHtmlOutputFromFile('dashboard')
      .setTitle('Lab Real-time Status')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
function getAppConfig() { return getMachinesConfig(); }

// =================== 4. LINE MESSAGING API (doPost) ===================
function doPost(e) {
  const event = JSON.parse(e.postData.contents).events[0];
  const replyToken = event.replyToken;
  const userId = event.source.userId; 
  
  if (event.type === 'message' && event.message.type === 'text') {
    handleMessage(replyToken, event.message.text, userId);
  } 
  else if (event.type === 'postback') {
    handlePostback(replyToken, event.postback.data, userId);
  }
  
  return ContentService.createTextOutput(JSON.stringify({'status': 'success'})).setMimeType(ContentService.MimeType.JSON);
}

function handlePostback(replyToken, data, userId) {
  let params = {};
  data.split('&').forEach(part => {
    let [key, val] = part.split('=');
    params[key] = val;
  });

  if (params.action === 'rate') {
    let score = params.score;
    let bid = params.bid; 

    let sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_RATINGS);
    let rows = sheet.getDataRange().getValues();
    
    let isVoted = false;
    for (let i = 1; i < rows.length; i++) { 
        if (String(rows[i][3]) === String(bid)) {
            isVoted = true;
            break;
        }
    }

    if (isVoted) {
        sendLineReply(replyToken, [{ type: "text", text: "⚠️ คุณได้ให้คะแนนไปแล้วครับ\nRating already submitted." }]);
    } else {
        sheet.appendRow([new Date(), userId, score, bid]);
        
        let msg = "ขอบคุณสำหรับการประเมินครับ! ⭐\nThanks for your rating! (" + score + "/5)";
        if (score >= 4) msg += " 😊";
        else if (score <= 2) msg += " 🙏 เราจะนำไปปรับปรุงครับ\nWe will use your feedback for further improvement.";
        
        sendLineReply(replyToken, [{ type: "text", text: msg }]);
    }
  }
}

function handleMessage(replyToken, msg, userId) {
    const cache = CacheService.getScriptCache();
    let state = cache.get("state_" + userId);

    if (msg === "ลงทะเบียน" || msg === "ข้อมูลส่วนตัว") {
      clearCache(userId);
      let userProfile = getUserProfileFromSheet(userId);
      if (userProfile) {
        replyUserProfile(replyToken, userProfile);
      } else {
        cache.put("state_" + userId, "REGIS_NAME", 600);
        sendLineReply(replyToken, [{ type: "text", text: "📝 **Registration / ลงทะเบียน**\n\nกรุณาพิมพ์ **ชื่อ-นามสกุล**:\nPlease enter your full name (First Name - Last Name):" }]);
      }
    }
    else if (msg === "จองเครื่องมือ" || msg === "ยกเลิก") {
      clearCache(userId);
      if (msg === "ยกเลิก") {
         sendLineReply(replyToken, [{ type: "text", text: "ยกเลิกรายการเรียบร้อย (Cancelled) ✅" }]);
      } else {
         let userProfile = getUserProfileFromSheet(userId);
         if (!userProfile) {
           sendLineReply(replyToken, [{ type: "text", text: "⚠️ คุณยังไม่เคยลงทะเบียน\nกรุณากดเมนู **'ลงทะเบียน'** ก่อนใช้งานระบบจองครับ\nYou are not yet registered." }]);
         } else if (userProfile.status === "Banned") {
           sendLineReply(replyToken, [{ type: "text", text: "🚫 **ไม่สามารถใช้งานได้**\nสิทธิ์การจองของคุณถูกระงับ (Banned)\n\nกรุณาติดต่อ Admin เพื่อตรวจสอบสิทธิ์ครับ" }]);
         } else if (userProfile.status === "Pending") {
           sendLineReply(replyToken, [{ type: "text", text: "⏳ **รอการอนุมัติ**\nบัญชีของคุณอยู่ระหว่างรอการยืนยัน (Pending)\n\nกรุณารอ Admin อนุมัติสิทธิ์ก่อนทำรายการครับ" }]);
         } else {
           replyFloorSelector(replyToken);
         }
      }
    } 
    else if (msg === "ประวัติการจอง" || msg === "เช็คประวัติ") {
      replyBookingHistory(replyToken, userId);
    }
    else if (msg === "จองเพิ่ม") {
      let userProfile = getUserProfileFromSheet(userId);
      if (userProfile && userProfile.status !== "Active") {
          sendLineReply(replyToken, [{ type: "text", text: "🚫 สิทธิ์การจองของคุณไม่สามารถทำรายการได้ในขณะนี้ กรุณาติดต่อ Admin" }]);
          return;
      }
      
      let cart = JSON.parse(cache.get("cart_" + userId) || "[]");
      if (cart.length > 0) {
        let currentMachine = cart[0].machine;
        replyFlexSchedule(replyToken, currentMachine, userId);
      } else {
        replyFloorSelector(replyToken);
      }
    }
    else if (msg.startsWith("เลือกชั้น_")) {
      let selectedFloor = msg.replace("เลือกชั้น_", "");
      replyMachineSelector(replyToken, selectedFloor);
    }
    else if (msg.startsWith("เลือก_")) {
      let machineName = msg.replace("เลือก_", "");
      replyFlexSchedule(replyToken, machineName, userId);
    }
    else if (msg.startsWith("เลือกจอง")) {
      addToCart(replyToken, msg, userId);
    }
    else if (msg === "ยืนยันการจอง") {
       let userProfile = getUserProfileFromSheet(userId);
       if (!userProfile) {
         sendLineReply(replyToken, [{ type: "text", text: "⚠️ กรุณาลงทะเบียนก่อนครับ\nRegistration required." }]);
       } else if (userProfile.status === "Banned") {
         sendLineReply(replyToken, [{ type: "text", text: "🚫 **ทำรายการไม่สำเร็จ**\nสิทธิ์การจองของคุณถูกระงับ\nกรุณาติดต่อ Admin ครับ" }]);
       } else if (userProfile.status === "Pending") {
         sendLineReply(replyToken, [{ type: "text", text: "⏳ **ทำรายการไม่สำเร็จ**\nบัญชีของคุณยังไม่อนุมัติ (Pending)\nกรุณารอ Admin ก่อนครับ" }]);
       } else {
         finalizeBooking(replyToken, userId, userProfile);
       }
    }
    else {
      handleRegistrationFlow(replyToken, msg, userId, state);
    }
}

// =================== 5. CORE FUNCTIONS ===================

function replyFloorSelector(replyToken) {
  let machines = getMachinesConfig();
  let floors = new Set();
  Object.values(machines).forEach(m => floors.add(m.floor));
  let sortedFloors = Array.from(floors).sort();

  let buttons = sortedFloors.map(f => ({
    "type": "button",
    "style": "primary",
    "color": COLOR_THEME.BUTTON_OK,
    "action": { "type": "message", "label": "ชั้น/Floor " + f, "text": "เลือกชั้น_" + f },
    "margin": "sm"
  }));

  let flex = {
    "type": "bubble",
    "body": {
      "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "text", "text": "กรุณาเลือกสถานที่ - Location", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg", "align": "center" },
        { "type": "separator", "margin": "md", "color": "#555555" },
        { "type": "box", "layout": "vertical", "margin": "md", "contents": buttons }
      ]
    }
  };
  sendLineReply(replyToken, [{ "type": "flex", "altText": "เลือกชั้น", "contents": flex }]);
}

function replyMachineSelector(replyToken, targetFloor) {
  let bubbles = [];
  let MACHINES_CONFIG = getMachinesConfig();

  Object.keys(MACHINES_CONFIG).forEach(name => {
    let info = MACHINES_CONFIG[name];
    if (info.floor === targetFloor) {
      let imageUrl = info.image || "https://via.placeholder.com/1024x500?text=No+Image";
      bubbles.push({
        "type": "bubble", "size": "kilo",
        "hero": { "type": "image", "url": imageUrl, "size": "full", "aspectRatio": "20:13", "aspectMode": "cover", "action": { "type": "message", "label": "เลือก", "text": "เลือก_" + name } },
        "body": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "contents": [{ "type": "text", "text": name, "weight": "bold", "size": "xl", "color": COLOR_THEME.TEXT_MAIN }, { "type": "text", "text": "กดปุ่มด้านล่างเพื่อดูตาราง\nTap below to view the schedule", "size": "sm", "color": COLOR_THEME.TEXT_SUB, "margin": "sm" }] },
        "footer": { "type": "box", "layout": "vertical", "spacing": "sm", "backgroundColor": COLOR_THEME.BODY_BG, "contents": [{ "type": "button", "style": "primary", "height": "sm", "color": COLOR_THEME.BUTTON_OK, "action": { "type": "message", "label": "ดูตารางจอง - View Bookings", "text": "เลือก_" + name } }], "flex": 0 }
      });
    }
  });

  if (bubbles.length === 0) {
    sendLineReply(replyToken, [{ type: "text", text: "❌ ไม่พบเครื่องมือในชั้นนี้\nNo equipment found on this floor." }]);
  } else {
    sendLineReply(replyToken, [{ "type": "flex", "altText": "เลือกเครื่องมือ", "contents": { "type": "carousel", "contents": bubbles } }]);
  }
}

function replyFlexSchedule(replyToken, machineName, currentUserId) {
  const MACHINES_CONFIG = getMachinesConfig();
  const BLOCKED_CONFIG = getBlockedSlotsConfig(); 
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS);
  const data = sheet.getDataRange().getValues();
  let bubbles = [];
  let today = new Date();

  let machineInfo = MACHINES_CONFIG[machineName];
  if (!machineInfo) return; 
  let slots = machineInfo.slots; 

  for (let i = 0; i < 7; i++) {
    let targetDate = new Date();
    targetDate.setDate(today.getDate() + i);
    let dayOfWeek = targetDate.getDay(); 
    if (dayOfWeek === 0 || dayOfWeek === 6) continue;

    let dateCheck = Utilities.formatDate(targetDate, Session.getScriptTimeZone(), "yyyy-MM-dd");
    let dateShow = Utilities.formatDate(targetDate, Session.getScriptTimeZone(), "dd/MM (EEE)");
    let buttonContents = [];

    let warningText = "";
    let warningColor = machineInfo.warnCol; 

    if (machineInfo.warnMsg && machineInfo.warnDays.includes(dayOfWeek)) {
      if (machineInfo.warnTime === "") {
        warningText = machineInfo.warnMsg; 
      } else if (slots.includes(machineInfo.warnTime)) {
        warningText = machineInfo.warnMsg; 
      }
    }

    slots.forEach(slot => {
      let bookerId = checkBooker(data, machineName, dateCheck, slot);
      
      let isBlocked = false;
      let blockMsg = "";
      if (BLOCKED_CONFIG[machineName] && BLOCKED_CONFIG[machineName][dateCheck] && BLOCKED_CONFIG[machineName][dateCheck][slot]) {
          isBlocked = true;
          blockMsg = BLOCKED_CONFIG[machineName][dateCheck][slot];
      }

      let color, labelText, action;

      if (isBlocked) { 
        color = COLOR_THEME.BUTTON_BLOCKED;
        labelText = `${slot} [${blockMsg}]`; 
        action = { "type": "postback", "label": labelText, "data": "none" };
      } 
      else if (bookerId === null) {
        color = COLOR_THEME.BUTTON_OK;
        labelText = slot; 
        action = { "type": "message", "label": labelText, "text": `เลือกจอง ${machineName} วันที่ ${dateCheck} เวลา ${slot}` };
      } else if (bookerId === currentUserId) {
        color = COLOR_THEME.BUTTON_SELF; 
        labelText = `${slot} [Booked by you]`; 
        action = { "type": "postback", "label": labelText, "data": "none" };
      } else {
        color = COLOR_THEME.BUTTON_FULL;
        labelText = `${slot} [Full]`;   
        action = { "type": "postback", "label": labelText, "data": "none" };
      }
      
      buttonContents.push({ "type": "button", "style": "primary", "color": color, "action": action, "height": "sm", "margin": "sm" });
    });

    let bodyContents = [{ "type": "text", "text": machineName, "align": "center", "weight": "bold", "color": COLOR_THEME.TEXT_SUB }, { "type": "separator", "margin": "md", "color": "#555555" }];
    
    if (warningText !== "") {
        bodyContents.push({ "type": "text", "text": warningText, "color": warningColor, "size": "xs", "wrap": true, "margin": "md", "weight": "bold" });
    }
    bodyContents.push(...buttonContents);

    bubbles.push({
      "type": "bubble",
      "header": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.HEADER_BG, "contents": [{ "type": "text", "text": dateShow, "color": COLOR_THEME.TEXT_MAIN, "weight": "bold", "size": "lg" }] },
      "body": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "contents": bodyContents }
    });
  }
  sendLineReply(replyToken, [{ "type": "flex", "altText": "ตารางเวลา", "contents": { "type": "carousel", "contents": bubbles } }]);
}

function addToCart(replyToken, msg, userId) {
  let match = msg.match(/เลือกจอง (.+) วันที่ (\d{4}-\d{2}-\d{2}) เวลา (.+)/);
  if (!match) return;
  let item = { machine: match[1], date: match[2], time: match[3] };
  
  let blockedData = getBlockedSlotsConfig();
  if (blockedData[item.machine] && blockedData[item.machine][item.date] && blockedData[item.machine][item.date][item.time]) {
     let blockMsg = blockedData[item.machine][item.date][item.time];
     sendLineReply(replyToken, [{ type: "text", text: `⚠️ ไม่สามารถจองได้ครับ\nช่วงเวลานี้ถูกปิด: ${blockMsg}\n\nCannot be booked: ${blockMsg}` }]);
     return;
  }

  const cache = CacheService.getScriptCache();
  let cart = JSON.parse(cache.get("cart_" + userId) || "[]");

  if (cart.length > 0) {
    let existingMachine = cart[0].machine;
    if (existingMachine !== item.machine) {
      sendLineReply(replyToken, [{ 
        type: "text", 
        text: `⚠️ **Cannot mix machines**\nไม่สามารถจองรวมกันได้ครับ\n\nYou have selected "${existingMachine}".\nPlease confirm or cancel it first.` 
      }]); 
      return; 
    }
  }

  let isDuplicate = cart.some(c => c.machine == item.machine && c.date == item.date && c.time == item.time);
  if (isDuplicate) { sendLineReply(replyToken, [{ type: "text", text: "⚠️ เลือกไปแล้วครับ (Already Selected)" }]); return; }
  cart.push(item);
  cache.put("cart_" + userId, JSON.stringify(cart), 600);
  replyCartConfirm(replyToken, cart);
}

function replyCartConfirm(replyToken, cart) {
  let itemsText = cart.map(c => `${c.machine} | ${c.time}`).join("\n");
  let flex = {
    "type": "bubble",
    "header": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.HEADER_BG, "contents": [{ "type": "text", "text": "Summary / สรุปรายการ", "color": COLOR_THEME.TEXT_MAIN, "weight": "bold" }] },
    "body": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "contents": [{ "type": "text", "text": "Cart Items (" + cart.length + ")", "weight": "bold", "color": COLOR_THEME.BUTTON_OK }, { "type": "separator", "margin": "md", "color": "#555555" }, { "type": "text", "text": itemsText, "wrap": true, "margin": "md", "size": "sm", "color": COLOR_THEME.TEXT_MAIN }] },
    "footer": { "type": "box", "layout": "horizontal", "spacing": "sm", "backgroundColor": COLOR_THEME.BODY_BG, "contents": [{ "type": "button", "style": "secondary", "action": { "type": "message", "label": "Add More/จองเพิ่ม", "text": "จองเพิ่ม" } }, { "type": "button", "style": "primary", "color": COLOR_THEME.BUTTON_OK, "action": { "type": "message", "label": "Confirm/ยืนยัน", "text": "ยืนยันการจอง" } }] }
  };
  sendLineReply(replyToken, [{ "type": "flex", "altText": "Booking Summary", "contents": flex }]);
}

function finalizeBooking(replyToken, userId, profile) {
  const lock = LockService.getScriptLock();
  try { lock.waitLock(10000); } catch (e) {
    sendLineReply(replyToken, [{ type: "text", text: "⚠️ System busy, please try again." }]); return;
  }

  const cache = CacheService.getScriptCache();
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS);
  let cart = JSON.parse(cache.get("cart_" + userId) || "[]");
  
  if (cart.length === 0) { 
    sendLineReply(replyToken, [{ type: "text", text: "❌ ตะกร้าว่างเปล่า (Cart is empty)" }]); 
    lock.releaseLock(); return; 
  }
  
  let bookingId = new Date().getTime().toString(); 
  let successCount = 0;
  let successItems = [];
  let failMsg = "";
  
  cart.forEach(item => {
    if (!checkAvailability(sheet.getDataRange().getValues(), item.machine, item.date, item.time)) {
      sheet.appendRow([new Date(), userId, item.machine, item.date, item.time, profile.name, profile.advisor, profile.year]);
      successCount++;
      successItems.push(`${item.machine} | ${item.time} (${item.date})`);
      markDataChanged(); 
    } else { 
      failMsg += `\n- ${item.machine} (${item.time}) Booked`; 
    }
  });
  
  clearCache(userId);
  lock.releaseLock();

  if (successCount > 0) {
    let listText = successItems.join("\n");
    let bodyContents = [
      { "type": "text", "text": `✅ Booking Success (${successCount})`, "weight": "bold", "color": COLOR_THEME.BUTTON_OK, "size": "md" },
      { "type": "separator", "margin": "md", "color": "#555555" },
      { "type": "text", "text": listText, "wrap": true, "margin": "md", "size": "sm", "color": COLOR_THEME.TEXT_MAIN },
      { "type": "text", "text": `User: ${profile.name}`, "margin": "sm", "size": "xs", "color": COLOR_THEME.TEXT_SUB }
    ];

    if (failMsg) {
       bodyContents.push({ "type": "separator", "margin": "md", "color": "#555555" });
       bodyContents.push({ "type": "text", "text": "⚠️ Failed Items:" + failMsg, "wrap": true, "margin": "md", "size": "xs", "color": "#FF5555" });
    }

    let flex = {
      "type": "bubble",
      "header": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.HEADER_BG, "contents": [{ "type": "text", "text": "Confirmation / ยืนยัน", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg" }] },
      "body": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "contents": bodyContents },
      "footer": { 
        "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "spacing": "sm",
        "contents": [
           { "type": "text", "text": "Rate Us / ให้คะแนนความพึงพอใจ", "size": "xs", "color": "#AAAAAA", "align": "center", "margin": "md" },
           {
              "type": "box", "layout": "horizontal", "spacing": "xs",
              "contents": [
                 { "type": "button", "action": { "type": "postback", "label": "1", "data": "action=rate&score=1&bid=" + bookingId }, "style": "secondary", "height": "sm" },
                 { "type": "button", "action": { "type": "postback", "label": "2", "data": "action=rate&score=2&bid=" + bookingId }, "style": "secondary", "height": "sm" },
                 { "type": "button", "action": { "type": "postback", "label": "3", "data": "action=rate&score=3&bid=" + bookingId }, "style": "secondary", "height": "sm" },
                 { "type": "button", "action": { "type": "postback", "label": "4", "data": "action=rate&score=4&bid=" + bookingId }, "style": "secondary", "height": "sm" },
                 { "type": "button", "action": { "type": "postback", "label": "5", "data": "action=rate&score=5&bid=" + bookingId }, "style": "secondary", "height": "sm" }
              ]
           }
        ] 
      }
    };
    sendLineReply(replyToken, [{ "type": "flex", "altText": "Booking Result", "contents": flex }]);
  } else {
    sendLineReply(replyToken, [{ "type": "text", "text": "⚠️ Booking Failed (Full / Error):\n" + failMsg }]);
  }
}

function checkBooker(data, machine, dateStr, timeStr) {
  for (let i = 1; i < data.length; i++) {
    let rowDate = Utilities.formatDate(new Date(data[i][3]), Session.getScriptTimeZone(), "yyyy-MM-dd");
    if (data[i][2] == machine && rowDate == dateStr && data[i][4] == timeStr) {
      return data[i][1]; 
    }
  }
  return null;
}

function checkAvailability(data, machine, dateStr, timeStr) {
  return checkBooker(data, machine, dateStr, timeStr) !== null;
}

function getUserProfileFromSheet(userId) {
  let sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_USERS);
  let data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === userId) {
      let rawDate = data[i][4];
      let dateDisplay = (rawDate instanceof Date) ? Utilities.formatDate(rawDate, "GMT+7", "dd/MM/yyyy HH:mm") : String(rawDate);
      let status = (data[i][5] !== undefined && data[i][5] !== "") ? String(data[i][5]).trim() : "Active";
      return { name: data[i][1], year: data[i][2], advisor: data[i][3], date: dateDisplay, status: status };
    }
  }
  return null;
}

function handleRegistrationFlow(replyToken, msg, userId, state) {
  const cache = CacheService.getScriptCache();
  if (state === "REGIS_NAME") {
    cache.put("temp_name_" + userId, msg, 600);
    cache.put("state_" + userId, "REGIS_YEAR", 600);
    sendLineReply(replyToken, [{ type: "text", text: "รับทราบ (Received)\n\nระบุ **ชั้นปี หรือ ตำแหน่ง** (เช่น ป.โท ปี 1):\nPlease specify **Year/Position** (e.g. Master Year 1):" }]);
  } else if (state === "REGIS_YEAR") {
    cache.put("temp_year_" + userId, msg, 600);
    cache.put("state_" + userId, "REGIS_ADVISOR", 600);
    sendLineReply(replyToken, [{ type: "text", text: "สุดท้ายครับ (Last Step)\n\nระบุ **ชื่ออาจารย์ที่ปรึกษา**:\nPlease specify **Advisor Name**:" }]);
  } else if (state === "REGIS_ADVISOR") {
    let name = cache.get("temp_name_" + userId);
    let year = cache.get("temp_year_" + userId);
    let advisor = msg;
    let regisDate = Utilities.formatDate(new Date(), "GMT+7", "dd/MM/yyyy HH:mm");
    let sheetUsers = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_USERS);
    sheetUsers.appendRow([userId, name, year, advisor, regisDate, "Active"]);
    clearCache(userId);
    let profile = { name: name, year: year, advisor: advisor, date: regisDate, status: "Active" };
    replyUserProfile(replyToken, profile);
  }
}

function replyUserProfile(replyToken, profile) {
  let statusText = profile.status === "Active" ? "🟢 ปกติ (Active)" : 
                   profile.status === "Banned" ? "🔴 ระงับสิทธิ์ (Banned)" : 
                   "⏳ รออนุมัติ (Pending)";

  let flex = {
    "type": "bubble",
    "header": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.HEADER_BG, "contents": [{ "type": "text", "text": "Registration Info / ข้อมูลสมาชิก", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg" }] },
    "body": {
      "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, 
      "contents": [
        { "type": "box", "layout": "vertical", "margin": "md", "spacing": "sm", "contents": [
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Name:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": profile.name, "wrap": true, "color": COLOR_THEME.TEXT_MAIN, "size": "sm", "flex": 5 } ] },
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Year:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": profile.year, "wrap": true, "color": COLOR_THEME.TEXT_MAIN, "size": "sm", "flex": 5 } ] },
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Advisor:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": profile.advisor, "wrap": true, "color": COLOR_THEME.TEXT_MAIN, "size": "sm", "flex": 5 } ] },
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Status:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": statusText, "weight": "bold", "color": (profile.status === "Active" ? "#4ADE80" : "#FF5555"), "size": "sm", "flex": 5 } ] }
          ]
        },
        { "type": "separator", "margin": "md", "color": "#555555" }, 
        { "type": "text", "text": "Regis Date: " + profile.date, "size": "xs", "color": COLOR_THEME.TEXT_SUB, "margin": "md", "align": "end" }
      ]
    },
    "footer": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "contents": [ { "type": "button", "style": "primary", "color": COLOR_THEME.BUTTON_OK, "action": { "type": "message", "label": "Booking / จองเครื่องมือ", "text": "จองเครื่องมือ" } } ] }
  };
  sendLineReply(replyToken, [{ "type": "flex", "altText": "Profile", "contents": flex }]);
}

function replyBookingHistory(replyToken, userId) {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS);
  const data = sheet.getDataRange().getValues();
  let myHistory = [];
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === userId) { 
      let rawDate = data[i][3]; 
      let dateStr = (rawDate instanceof Date) ? Utilities.formatDate(rawDate, "GMT+7", "dd/MM/yyyy") : String(rawDate);
      myHistory.push({ machine: data[i][2], date: dateStr, time: data[i][4], timestamp: new Date(data[i][0]).getTime() });
    }
  }
  if (myHistory.length === 0) {
    sendLineReply(replyToken, [{ type: "text", text: "📭 คุณยังไม่มีประวัติการจองครับ (No Booking History)" }]);
    return;
  }
  myHistory.sort((a, b) => b.timestamp - a.timestamp);
  let recentHistory = myHistory.slice(0, 10);
  let historyRows = [];
  recentHistory.forEach(item => {
    historyRows.push({
      "type": "box", "layout": "vertical", "margin": "md",
      "contents": [
        { "type": "box", "layout": "baseline", "contents": [
            { "type": "text", "text": item.date, "color": COLOR_THEME.TEXT_SUB, "size": "xs", "flex": 2 },
            { "type": "text", "text": item.machine, "color": COLOR_THEME.TEXT_MAIN, "weight": "bold", "size": "sm", "flex": 4 },
            { "type": "text", "text": item.time, "color": COLOR_THEME.BUTTON_OK, "size": "xs", "align": "end", "flex": 3 }
          ]
        },
        { "type": "separator", "margin": "sm", "color": "#444444" } 
      ]
    });
  });
  let flex = {
    "type": "bubble",
    "header": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.HEADER_BG, "contents": [ { "type": "text", "text": "🕒 Recent History / ประวัติล่าสุด", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg" } ] },
    "body": { "type": "box", "layout": "vertical", "backgroundColor": COLOR_THEME.BODY_BG, "contents": [ ...historyRows, { "type": "text", "text": "*Showing last 10 bookings", "size": "xxs", "color": "#666666", "margin": "lg", "align": "center" } ] }
  };
  sendLineReply(replyToken, [{ "type": "flex", "altText": "History", "contents": flex }]);
}

function clearCache(userId) {
  const cache = CacheService.getScriptCache();
  cache.removeAll(["state_" + userId, "cart_" + userId, "temp_name_" + userId, "temp_year_" + userId]);
}

function sendLineReply(replyToken, messages) {
  UrlFetchApp.fetch('https://api.line.me/v2/bot/message/reply', { 'headers': { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + CHANNEL_ACCESS_TOKEN }, 'method': 'post', 'payload': JSON.stringify({ 'replyToken': replyToken, 'messages': messages }) });
}

// =================== 7. TIMELINE DATA ===================

function getTimelineData() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS);
  const data = sheet.getDataRange().getValues();
  const MACHINES_CONFIG = getMachinesConfig();
  const BLOCKED_CONFIG = getBlockedSlotsConfig(); 

  let schedule = [];
  let today = new Date();
  let dayCount = 0;
  let currentCheckDate = new Date(today);

  while (dayCount < 6) { 
    if (currentCheckDate.getDay() !== 0 && currentCheckDate.getDay() !== 6) {
      let dateStr = Utilities.formatDate(currentCheckDate, "GMT+7", "yyyy-MM-dd");
      let displayDate = Utilities.formatDate(currentCheckDate, "GMT+7", "dd/MM (EEE)");
      
      let rawBookings = [];

      for (let i = 1; i < data.length; i++) {
        let rowDateStr = Utilities.formatDate(new Date(data[i][3]), "GMT+7", "yyyy-MM-dd");
        
        if (rowDateStr === dateStr) {
          let machine = data[i][2];
          if (!MACHINES_CONFIG[machine]) continue;
          
          let timeStr = data[i][4];
          let userName = data[i][5];
          let advisor = data[i][6];
          let [s, e] = timeStr.split("-");
          
          let startH = parseInt(s.split(":")[0]);
          let endH = parseInt(e.split(":")[0]);
          let bookingTimestamp = new Date(data[i][0]).getTime(); 

          rawBookings.push({
            machine: machine, 
            user: userName, 
            advisor: advisor,
            start: startH, 
            duration: endH - startH,
            end: endH,
            timestamp: bookingTimestamp 
          });
        }
      }

      Object.keys(BLOCKED_CONFIG).forEach(machine => {
        if (BLOCKED_CONFIG[machine][dateStr]) {
            Object.keys(BLOCKED_CONFIG[machine][dateStr]).forEach(timeStr => {
               let blockMsg = BLOCKED_CONFIG[machine][dateStr][timeStr];
               let [s, e] = timeStr.split("-");
               let startH = parseInt(s.split(":")[0]);
               let endH = parseInt(e.split(":")[0]);
               
               rawBookings.push({
                   machine: machine,
                   user: "⛔ " + blockMsg, 
                   advisor: "",
                   start: startH,
                   duration: endH - startH,
                   end: endH,
                   timestamp: 0 
               });
            });
        }
      });
      
      schedule.push({ date: displayDate, bookings: rawBookings });
      dayCount++;
    }
    currentCheckDate.setDate(currentCheckDate.getDate() + 1);
  }
  return schedule;
}

// === Real-time Trigger ===
function markDataChanged() {
  PropertiesService.getScriptProperties().setProperty('LAST_UPDATE', new Date().getTime());
}

function getLastUpdateTimestamp() {
  return PropertiesService.getScriptProperties().getProperty('LAST_UPDATE') || 0;
}