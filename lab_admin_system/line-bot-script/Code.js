// =================== 1. MASTER CONFIG ===================
const props = PropertiesService.getScriptProperties();
const CHANNEL_ACCESS_TOKEN = props.getProperty('LINE_TOKEN'); 
const SHEET_ID = props.getProperty('SHEET_ID'); 

// 📌 ดึงลิงก์ PDF จาก Script Properties
const PDF_PRIVACY_NOTICE_URL = props.getProperty('PDF_URL');

const SHEET_BOOKINGS = 'Bookings';
const SHEET_USERS = 'Users';
const SHEET_MACHINES = 'Machines'; 
const SHEET_RATINGS = 'Ratings'; 
const SHEET_BLOCKED = 'BlockedSlots'; 
const SHEET_WAITING = 'WaitingList'; 

const COLOR_THEME = { 
  HEADER_BG: "#88304E", 
  BODY_BG: "#2C2C2C", 
  BUTTON_OK: "#88304E", 
  BUTTON_FULL: "#4F4F4F", 
  BUTTON_SELF: "#522546", 
  BUTTON_BLOCKED: "#666666", 
  BUTTON_WAIT: "#D97706", 
  TEXT_MAIN: "#FFFFFF", 
  TEXT_SUB: "#AAAAAA" 
};

// =================== 2. DYNAMIC CONFIG ===================
function getMachinesConfig() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_MACHINES); 
  const data = sheet.getDataRange().getValues(); 
  let config = {};
  
  for (let i = 1; i < data.length; i++) {
    if (data[i][5] === 'Active') { 
      let wDays = []; 
      if (data[i][6]) {
        wDays = String(data[i][6]).split(',').map(d => parseInt(d.trim()));
      }
      
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
        
        slots.forEach(s => config[machine][dateStr][s] = msg);
      }
    }
  } catch (e) { 
    console.log(e); 
  } 
  return config;
}

// =================== 3. WEB APP ROUTING ===================
function doGet(e) {
  if (e.parameter && e.parameter.page === 'timeline') {
    return HtmlService.createHtmlOutputFromFile('timeline_view').setTitle('Lab Timeline');
  }
  return HtmlService.createHtmlOutputFromFile('dashboard').setTitle('Lab Status');
}

// =================== 4. LINE MESSAGING API ===================
function doPost(e) {
  const event = JSON.parse(e.postData.contents).events[0]; 
  const replyToken = event.replyToken; 
  const userId = event.source.userId; 
  
  if (event.type === 'message' && event.message.type === 'text') {
    handleMessage(replyToken, event.message.text, userId);
  } else if (event.type === 'postback') {
    handlePostback(replyToken, event.postback.data, userId);
  }
  
  return ContentService.createTextOutput(JSON.stringify({'status': 'success'})).setMimeType(ContentService.MimeType.JSON);
}

function handlePostback(replyToken, data, userId) {
  let params = {}; 
  data.split('&').forEach(part => { 
    let [key, val] = part.split('='); 
    params[key] = decodeURIComponent(val); 
  });

  // ⭐️ 1. จัดการ PDPA 
  if (params.action === 'accept_pdpa') {
    const cache = CacheService.getScriptCache();
    let isUpdate = cache.get("is_update_" + userId);
    
    if (isUpdate) {
       cache.put("state_" + userId, "UPDATE_EMAIL", 600);
       sendLineReply(replyToken, [{ type: "text", text: "✅ ยอมรับเงื่อนไขเรียบร้อย (Terms accepted)\n\n📧 กรุณาพิมพ์ **Email** ของคุณ:\n(Please enter your Email):" }]);
    } else {
       cache.put("state_" + userId, "REGIS_NAME", 600);
       sendLineReply(replyToken, [{ type: "text", text: "✅ ยอมรับเงื่อนไขเรียบร้อย (Terms accepted)\n\n📝 กรุณาพิมพ์ **ชื่อ-นามสกุล**:\n(Please enter your Full Name):" }]);
    }
    return;
  }
  else if (params.action === 'decline_pdpa') {
    sendLineReply(replyToken, [{ type: "text", text: "❌ ยกเลิกการทำรายการ (Cancelled)\n\nระบบจำเป็นต้องได้รับความยินยอม เพื่อใช้ข้อมูลในการยืนยันตัวตนและการติดต่อกรณีฉุกเฉินครับ\n(Consent is required to use the system.)" }]); 
    return;
  }

  // 2. จัดการคะแนน
  else if (params.action === 'rate') {
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
      sendLineReply(replyToken, [{ type: "text", text: "⚠️ คุณได้ให้คะแนนไปแล้วครับ" }]);
    } else { 
      sheet.appendRow([new Date(), userId, score, bid]); 
      let msg = `ขอบคุณสำหรับการประเมินครับ! ⭐ (${score}/5)`; 
      if (score <= 2) msg += "\n🙏 เราจะนำไปปรับปรุงครับ"; 
      sendLineReply(replyToken, [{ type: "text", text: msg }]); 
    }
  }

  // 3. ลงคิวรอ
  else if (params.action === 'waitlist') {
    let m = params.m; 
    let d = params.d; 
    let t = params.t;
    let profile = checkUserGate(replyToken, userId); 
    
    if (!profile) return; 

    let sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_WAITING);
    sheet.appendRow([new Date(), userId, m, d, t]);
    sendLineReply(replyToken, [{ type: "text", text: `📝 บันทึกรายชื่อรอคิวสำเร็จ!\nหากมีคิวว่าง ระบบจะส่งอีเมลแจ้งเตือนไปที่ ${profile.email} ทันทีครับ` }]);
  }

  // 4. ยกเลิกคิว
  else if (params.action === 'cancel') {
    let profile = checkUserGate(replyToken, userId); 
    if (!profile) return;
    
    let m = params.m; 
    let d = params.d; 
    let t = params.t;
    
    let dateParts = d.split('-'); 
    let timeParts = t.split('-')[0].split(':');
    let bookDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2], timeParts[0], timeParts[1], 0);
    let now = new Date(); 
    let diffHours = (bookDate.getTime() - now.getTime()) / (1000 * 60 * 60);
    
    if (diffHours < 24) { 
      sendLineReply(replyToken, [{ type: "text", text: `🚫 ไม่สามารถยกเลิกได้ล่วงหน้าน้อยกว่า 24 ชม.\n(เหลือเวลา ${diffHours.toFixed(1)} ชม.)` }]); 
      return; 
    }

    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS); 
    const data = sheet.getDataRange().getValues(); 
    let deleted = false;
    
    for (let i = data.length - 1; i >= 1; i--) {
       let rowDate = Utilities.formatDate(new Date(data[i][3]), Session.getScriptTimeZone(), "yyyy-MM-dd");
       if (data[i][1] === userId && data[i][2] === m && rowDate === d && data[i][4] === t) { 
         sheet.deleteRow(i + 1); 
         deleted = true; 
         markDataChanged(); 
         break; 
       }
    }
    
    if (deleted) { 
      sendLineReply(replyToken, [{ type: "text", text: `✅ ยกเลิกการจองสำเร็จ!\nรายการ: ${m}\nวันที่: ${d} (${t})` }]); 
      checkWaitingListAndNotify(m, d, t); 
    } else {
      sendLineReply(replyToken, [{ type: "text", text: "⚠️ ไม่พบข้อมูลการจองนี้แล้วครับ" }]);
    }
  }
}

// ⭐️ ระบบด่านตรวจ
function checkUserGate(replyToken, userId) {
  let userProfile = getUserProfileFromSheet(userId);
  
  if (!userProfile) { 
    replyPDPAConsent(replyToken, false); 
    return null; 
  }
  
  if (!userProfile.email || !userProfile.phone) {
      const cache = CacheService.getScriptCache();
      cache.put("is_update_" + userId, "true", 600);
      replyPDPAConsent(replyToken, true); 
      return null;
  }
  
  if (userProfile.status === "Banned") { 
    sendLineReply(replyToken, [{ type: "text", text: "🚫 สิทธิ์การใช้งานของคุณถูกระงับ" }]); 
    return null; 
  }
  
  if (userProfile.status === "Pending") { 
    sendLineReply(replyToken, [{ type: "text", text: "⏳ บัญชีอยู่ระหว่างรอการยืนยัน" }]); 
    return null; 
  }
  
  return userProfile;
}

function handleMessage(replyToken, msg, userId) {
    const cache = CacheService.getScriptCache();
    let state = cache.get("state_" + userId);

    if (msg === "ลงทะเบียน" || msg === "ข้อมูลส่วนตัว") {
      clearCache(userId); 
      let userProfile = getUserProfileFromSheet(userId);
      if (userProfile && userProfile.email && userProfile.phone) {
        replyUserProfile(replyToken, userProfile);
      } else {
        checkUserGate(replyToken, userId); 
      }
    }
    else if (msg === "ยกเลิก" || msg === "ยกเลิกการทำรายการ") {
      clearCache(userId); 
      sendLineReply(replyToken, [{ type: "text", text: "ยกเลิกคำสั่งเดิมเรียบร้อย ✅" }]);
    }
    else if (msg === "จองเครื่องมือ") {
      clearCache(userId); 
      let profile = checkUserGate(replyToken, userId); 
      if (profile) replyFloorSelector(replyToken);
    } 
    else if (msg === "ประวัติการจอง" || msg === "เช็คประวัติ") {
      clearCache(userId); 
      let profile = checkUserGate(replyToken, userId); 
      if (profile) replyBookingHistory(replyToken, userId);
    }
    else if (msg === "ยกเลิกการจอง" || msg === "จัดการคิว") {
      clearCache(userId); 
      let profile = checkUserGate(replyToken, userId); 
      if (profile) replyUpcomingBookings(replyToken, userId);
    }
    else if (msg === "จองเพิ่ม") {
      let profile = checkUserGate(replyToken, userId); 
      if (!profile) return;
      
      let cart = JSON.parse(cache.get("cart_" + userId) || "[]");
      if (cart.length > 0) {
        replyFlexSchedule(replyToken, cart[0].machine, userId); 
      } else {
        replyFloorSelector(replyToken);
      }
    }
    else if (msg.startsWith("เลือกชั้น_")) {
      replyMachineSelector(replyToken, msg.replace("เลือกชั้น_", ""));
    }
    else if (msg.startsWith("เลือก_")) {
      replyFlexSchedule(replyToken, msg.replace("เลือก_", ""), userId);
    }
    else if (msg.startsWith("เลือกจอง")) {
      addToCart(replyToken, msg, userId);
    }
    else if (msg === "ยืนยันการจอง") {
       let profile = checkUserGate(replyToken, userId); 
       if (profile) finalizeBooking(replyToken, userId, profile);
    }
    else {
      handleRegistrationFlow(replyToken, msg, userId, state);
    }
}

// =================== 5. CORE FUNCTIONS ===================

function replyPDPAConsent(replyToken, isUpdate = false) {
  // ⭐️ แก้ไขคำอธิบายให้กระชับ เป็น 2 ภาษา
  let textLine1 = isUpdate ? "⚠️ ประกาศปรับปรุงนโยบาย (Policy Update)" : "🔒 นโยบายความเป็นส่วนตัว (PDPA)";
  let textLine2 = isUpdate 
      ? "ระบบได้มีการปรับปรุงนโยบายความเป็นส่วนตัว (PDPA) กรุณาอ่านและกดยอมรับเงื่อนไขเพื่อใช้งานระบบต่อไปครับ\n\nOur Privacy Policy (PDPA) has been updated. Please read and accept the terms to continue using the system."
      : "กรุณาอ่านนโยบายความเป็นส่วนตัว (Privacy Notice) และกดยอมรับเงื่อนไขก่อนเริ่มลงทะเบียนครับ\n\nPlease read our Privacy Notice and accept the terms to register.";

  let flex = {
    "type": "bubble",
    "header": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.HEADER_BG,
      "contents": [
        { "type": "text", "text": textLine1, "color": COLOR_THEME.TEXT_MAIN, "weight": "bold", "size": "md" }
      ]
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "text", "text": textLine2, "color": COLOR_THEME.TEXT_MAIN, "wrap": true, "size": "sm" }
      ]
    },
    "footer": {
      "type": "box",
      "layout": "vertical",
      "spacing": "sm",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "button", "style": "secondary", "action": { "type": "uri", "label": "อ่าน Privacy Notice", "uri": PDF_PRIVACY_NOTICE_URL } },
        { "type": "button", "style": "primary", "color": "#79E1B6", "action": { "type": "postback", "label": "ยอมรับ (Accept)", "data": "action=accept_pdpa" } },
        { "type": "button", "style": "primary", "color": "#FF5555", "action": { "type": "postback", "label": "ไม่ยอมรับ (Decline)", "data": "action=decline_pdpa" } }
      ]
    }
  };
  sendLineReply(replyToken, [{ "type": "flex", "altText": "กรุณายอมรับเงื่อนไข PDPA", "contents": flex }]);
}

function handleRegistrationFlow(replyToken, msg, userId, state) {
  const cache = CacheService.getScriptCache();
  
  if (state === "REGIS_NAME") {
    cache.put("temp_name_" + userId, msg, 600); 
    cache.put("state_" + userId, "REGIS_YEAR", 600);
    sendLineReply(replyToken, [{ type: "text", text: "🎓 ระบุ **ชั้นปี หรือ ตำแหน่ง** (เช่น ป.โท ปี 1):\n(Please enter your Year/Position):" }]);
  } 
  else if (state === "REGIS_YEAR") {
    cache.put("temp_year_" + userId, msg, 600); 
    cache.put("state_" + userId, "REGIS_ADVISOR", 600);
    sendLineReply(replyToken, [{ type: "text", text: "👨‍🏫 ระบุ **ชื่ออาจารย์ที่ปรึกษา**:\n(Please enter your Advisor's name):" }]);
  } 
  else if (state === "REGIS_ADVISOR") {
    cache.put("temp_adv_" + userId, msg, 600); 
    cache.put("state_" + userId, "REGIS_EMAIL", 600);
    // ⭐️ ปรับคำถาม Email เป็น 2 ภาษา
    sendLineReply(replyToken, [{ type: "text", text: "📧 กรุณาพิมพ์ **Email** ของคุณ:\n(Please enter your Email):" }]);
  } 
  else if (state === "REGIS_EMAIL") {
    let email = msg.trim(); 
    if (!email.includes("@")) { 
      sendLineReply(replyToken, [{ type: "text", text: "⚠️ รูปแบบ Email ไม่ถูกต้อง กรุณาพิมพ์ใหม่อีกครั้ง\n(Invalid Email format. Please try again):" }]); 
      return; 
    }
    cache.put("temp_email_" + userId, email, 600); 
    cache.put("state_" + userId, "REGIS_PHONE", 600);
    // ⭐️ ปรับคำถามเบอร์โทรเป็น 2 ภาษา
    sendLineReply(replyToken, [{ type: "text", text: "📱 กรุณาระบุ **เบอร์โทรศัพท์** ของคุณ (เช่น 0812345678):\n(Please enter your Phone number):" }]);
  } 
  else if (state === "REGIS_PHONE") {
    let phone = msg.trim(); 
    let name = cache.get("temp_name_" + userId); 
    let year = cache.get("temp_year_" + userId); 
    let advisor = cache.get("temp_adv_" + userId); 
    let email = cache.get("temp_email_" + userId);
    let regisDate = Utilities.formatDate(new Date(), "GMT+7", "dd/MM/yyyy HH:mm");
    
    let sheetUsers = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_USERS);
    sheetUsers.appendRow([userId, name, year, advisor, regisDate, "Active", email, phone]);
    clearCache(userId);
    
    let profile = { name: name, year: year, advisor: advisor, date: regisDate, status: "Active", email: email, phone: phone };
    replyUserProfile(replyToken, profile);
  }
  else if (state === "UPDATE_EMAIL") {
    let email = msg.trim(); 
    if (!email.includes("@")) { 
      sendLineReply(replyToken, [{ type: "text", text: "⚠️ รูปแบบ Email ไม่ถูกต้อง กรุณาพิมพ์ใหม่อีกครั้ง\n(Invalid Email format. Please try again):" }]); 
      return; 
    }
    cache.put("temp_email_" + userId, email, 600); 
    cache.put("state_" + userId, "UPDATE_PHONE", 600);
    sendLineReply(replyToken, [{ type: "text", text: "📱 กรุณาระบุ **เบอร์โทรศัพท์** ของคุณ (เช่น 0812345678):\n(Please enter your Phone number):" }]);
  } 
  else if (state === "UPDATE_PHONE") {
    let phone = msg.trim(); 
    let email = cache.get("temp_email_" + userId);
    
    let sheetUsers = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_USERS);
    let data = sheetUsers.getDataRange().getValues(); 
    let headers = data[0];
    
    let emailColIdx = headers.indexOf('Email'); 
    if (emailColIdx === -1) { 
      emailColIdx = headers.length; 
      sheetUsers.getRange(1, emailColIdx + 1).setValue('Email'); 
    }
    
    let phoneColIdx = headers.indexOf('Phone'); 
    if (phoneColIdx === -1) { 
      phoneColIdx = headers.length; 
      sheetUsers.getRange(1, phoneColIdx + 1).setValue('Phone'); 
    }
    
    for (let i = 1; i < data.length; i++) {
        if (data[i][0] === userId) { 
            sheetUsers.getRange(i + 1, emailColIdx + 1).setValue(email); 
            sheetUsers.getRange(i + 1, phoneColIdx + 1).setValue(phone); 
            break; 
        }
    }
    
    clearCache(userId);
    // ⭐️ ข้อความแจ้งเตือนอัปเดตสำเร็จ
    sendLineReply(replyToken, [{ type: "text", text: "✅ อัปเดตข้อมูลสำเร็จ! คุณสามารถใช้งานระบบได้ตามปกติครับ\n(Update successful! You can now use the system.)" }]);
  }
}

function replyUpcomingBookings(replyToken, userId) {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS); 
  const data = sheet.getDataRange().getValues(); 
  let upcoming = []; 
  let now = new Date();
  
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === userId) { 
      let dateStr = Utilities.formatDate(new Date(data[i][3]), Session.getScriptTimeZone(), "yyyy-MM-dd"); 
      let timeStr = data[i][4];
      let dateParts = dateStr.split('-'); 
      let timeParts = timeStr.split('-')[0].split(':'); 
      let bookDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2], timeParts[0], timeParts[1], 0);
      
      if (bookDate > now) {
        upcoming.push({ machine: data[i][2], date: dateStr, time: timeStr, bookDateObj: bookDate });
      }
    }
  }
  
  if (upcoming.length === 0) { 
    sendLineReply(replyToken, [{ type: "text", text: "📭 คุณไม่มีรายการจองล่วงหน้าที่สามารถยกเลิกได้ครับ" }]); 
    return; 
  }
  
  upcoming.sort((a, b) => a.bookDateObj - b.bookDateObj);
  
  let bubbles = upcoming.slice(0, 10).map(item => { 
    let pbData = `action=cancel&m=${encodeURIComponent(item.machine)}&d=${item.date}&t=${item.time}`; 
    return {
      "type": "bubble",
      "body": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.BODY_BG,
        "spacing": "sm",
        "contents": [
          { "type": "text", "text": "📝 คิวที่จองไว้ล่วงหน้า", "color": COLOR_THEME.TEXT_MAIN, "weight": "bold", "size": "md" },
          { "type": "separator", "margin": "sm", "color": "#555555" },
          { "type": "text", "text": item.machine, "color": COLOR_THEME.TEXT_SUB, "weight": "bold", "size": "xl", "wrap": true },
          { "type": "text", "text": `วันที่: ${item.date}`, "color": COLOR_THEME.TEXT_MAIN, "size": "sm" },
          { "type": "text", "text": `เวลา: ${item.time}`, "color": COLOR_THEME.TEXT_MAIN, "size": "sm" }
        ]
      },
      "footer": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.BODY_BG,
        "contents": [
          { "type": "button", "style": "primary", "color": "#D93025", "action": { "type": "postback", "label": "❌ ยกเลิกคิวนี้", "data": pbData } },
          { "type": "text", "text": "*ยกเลิกได้ล่วงหน้า 24 ชม.", "size": "xxs", "color": "#888888", "align": "center", "margin": "sm" }
        ]
      }
    }; 
  });
  
  sendLineReply(replyToken, [{ "type": "flex", "altText": "จัดการคิวของคุณ", "contents": { "type": "carousel", "contents": bubbles } }]);
}

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
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "text", "text": "กรุณาเลือกสถานที่", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg", "align": "center" },
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
        "type": "bubble",
        "size": "kilo",
        "hero": { "type": "image", "url": imageUrl, "size": "full", "aspectRatio": "20:13", "aspectMode": "cover", "action": { "type": "message", "label": "เลือก", "text": "เลือก_" + name } },
        "body": {
          "type": "box",
          "layout": "vertical",
          "backgroundColor": COLOR_THEME.BODY_BG,
          "contents": [
            { "type": "text", "text": name, "weight": "bold", "size": "xl", "color": COLOR_THEME.TEXT_MAIN },
            { "type": "text", "text": "กดปุ่มด้านล่างเพื่อดูตาราง", "size": "sm", "color": COLOR_THEME.TEXT_SUB, "margin": "sm" }
          ]
        },
        "footer": {
          "type": "box",
          "layout": "vertical",
          "spacing": "sm",
          "backgroundColor": COLOR_THEME.BODY_BG,
          "contents": [
            { "type": "button", "style": "primary", "height": "sm", "color": COLOR_THEME.BUTTON_OK, "action": { "type": "message", "label": "ดูตารางจอง", "text": "เลือก_" + name } }
          ],
          "flex": 0
        }
      });
    }
  });
  
  if (bubbles.length === 0) {
    sendLineReply(replyToken, [{ type: "text", text: "❌ ไม่พบเครื่องมือ" }]);
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
      if (machineInfo.warnTime === "" || slots.includes(machineInfo.warnTime)) {
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
      } 
      else if (bookerId === currentUserId) { 
        color = COLOR_THEME.BUTTON_SELF; 
        labelText = `${slot} [คิวของคุณ]`; 
        action = { "type": "postback", "label": labelText, "data": "none" }; 
      } 
      else { 
        color = COLOR_THEME.BUTTON_WAIT; 
        labelText = `${slot} [ลงคิวรอ]`; 
        let pbData = `action=waitlist&m=${encodeURIComponent(machineName)}&d=${dateCheck}&t=${slot}`; 
        action = { "type": "postback", "label": labelText, "data": pbData }; 
      }
      
      buttonContents.push({ "type": "button", "style": "primary", "color": color, "action": action, "height": "sm", "margin": "sm" });
    });
    
    let bodyContents = [
      { "type": "text", "text": machineName, "align": "center", "weight": "bold", "color": COLOR_THEME.TEXT_SUB },
      { "type": "separator", "margin": "md", "color": "#555555" }
    ];
    
    if (warningText !== "") {
      bodyContents.push({ "type": "text", "text": warningText, "color": warningColor, "size": "xs", "wrap": true, "margin": "md", "weight": "bold" }); 
    }
    
    bodyContents.push(...buttonContents);
    
    bubbles.push({
      "type": "bubble",
      "header": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.HEADER_BG,
        "contents": [{ "type": "text", "text": dateShow, "color": COLOR_THEME.TEXT_MAIN, "weight": "bold", "size": "lg" }]
      },
      "body": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.BODY_BG,
        "contents": bodyContents
      }
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
    sendLineReply(replyToken, [{ type: "text", text: `⚠️ ช่วงเวลานี้ถูกปิดครับ` }]); 
    return; 
  }
  
  const cache = CacheService.getScriptCache(); 
  let cart = JSON.parse(cache.get("cart_" + userId) || "[]");
  
  if (cart.length > 0 && cart[0].machine !== item.machine) { 
    sendLineReply(replyToken, [{ type: "text", text: `⚠️ ไม่สามารถจองรวมเครื่องกันได้ครับ` }]); 
    return; 
  }
  
  if (cart.some(c => c.machine == item.machine && c.date == item.date && c.time == item.time)) { 
    sendLineReply(replyToken, [{ type: "text", text: "⚠️ เลือกไปแล้วครับ" }]); 
    return; 
  }
  
  cart.push(item); 
  cache.put("cart_" + userId, JSON.stringify(cart), 600); 
  replyCartConfirm(replyToken, cart);
}

function replyCartConfirm(replyToken, cart) {
  let itemsText = cart.map(c => `${c.machine} | ${c.time}`).join("\n");
  
  let flex = {
    "type": "bubble",
    "header": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.HEADER_BG,
      "contents": [{ "type": "text", "text": "สรุปรายการจอง", "color": COLOR_THEME.TEXT_MAIN, "weight": "bold" }]
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "text", "text": "ตะกร้า (" + cart.length + ")", "weight": "bold", "color": COLOR_THEME.BUTTON_OK },
        { "type": "separator", "margin": "md", "color": "#555555" },
        { "type": "text", "text": itemsText, "wrap": true, "margin": "md", "size": "sm", "color": COLOR_THEME.TEXT_MAIN }
      ]
    },
    "footer": {
      "type": "box",
      "layout": "horizontal",
      "spacing": "sm",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "button", "style": "secondary", "action": { "type": "message", "label": "จองเพิ่ม", "text": "จองเพิ่ม" } },
        { "type": "button", "style": "primary", "color": COLOR_THEME.BUTTON_OK, "action": { "type": "message", "label": "ยืนยัน", "text": "ยืนยันการจอง" } }
      ]
    }
  };
  sendLineReply(replyToken, [{ "type": "flex", "altText": "Booking Summary", "contents": flex }]);
}

function finalizeBooking(replyToken, userId, profile) {
  const lock = LockService.getScriptLock(); 
  try { 
    lock.waitLock(10000); 
  } catch (e) { 
    sendLineReply(replyToken, [{ type: "text", text: "⚠️ ระบบยุ่ง กรุณาลองใหม่" }]); 
    return; 
  }
  
  const cache = CacheService.getScriptCache(); 
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_BOOKINGS); 
  let cart = JSON.parse(cache.get("cart_" + userId) || "[]");
  
  if (cart.length === 0) { 
    sendLineReply(replyToken, [{ type: "text", text: "❌ ตะกร้าว่างเปล่า" }]); 
    lock.releaseLock(); 
    return; 
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
      failMsg += `\n- ${item.machine} (${item.time}) เต็มแล้ว`; 
    }
  });
  
  clearCache(userId); 
  lock.releaseLock();
  
  if (successCount > 0) {
    let listText = successItems.join("\n"); 
    
    let bodyContents = [
      { "type": "text", "text": `✅ ทำรายการสำเร็จ (${successCount})`, "weight": "bold", "color": COLOR_THEME.BUTTON_OK, "size": "md" },
      { "type": "separator", "margin": "md", "color": "#555555" },
      { "type": "text", "text": listText, "wrap": true, "margin": "md", "size": "sm", "color": COLOR_THEME.TEXT_MAIN }
    ];
    
    if (failMsg) { 
      bodyContents.push({ "type": "separator", "margin": "md", "color": "#555555" }); 
      bodyContents.push({ "type": "text", "text": "⚠️ ไม่สำเร็จ:" + failMsg, "wrap": true, "margin": "md", "size": "xs", "color": "#FF5555" }); 
    }
    
    let flex = {
      "type": "bubble",
      "header": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.HEADER_BG,
        "contents": [{ "type": "text", "text": "ยืนยันการจอง", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg" }]
      },
      "body": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.BODY_BG,
        "contents": bodyContents
      },
      "footer": {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": COLOR_THEME.BODY_BG,
        "spacing": "sm",
        "contents": [
          { "type": "text", "text": "ให้คะแนนความพึงพอใจ", "size": "xs", "color": "#AAAAAA", "align": "center", "margin": "md" },
          {
            "type": "box",
            "layout": "horizontal",
            "spacing": "xs",
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
    sendLineReply(replyToken, [{ "type": "text", "text": "⚠️ ล้มเหลว:\n" + failMsg }]);
  }
}

function checkBooker(data, machine, dateStr, timeStr) { 
  for (let i = 1; i < data.length; i++) { 
    let rowDate = Utilities.formatDate(new Date(data[i][3]), Session.getScriptTimeZone(), "yyyy-MM-dd"); 
    if (data[i][2] == machine && rowDate == dateStr && data[i][4] == timeStr) return data[i][1]; 
  } 
  return null; 
}

function checkAvailability(data, machine, dateStr, timeStr) { 
  return checkBooker(data, machine, dateStr, timeStr) !== null; 
}

function checkWaitingListAndNotify(machine, dateStr, timeStr) {
  const sheetWait = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_WAITING); 
  if (!sheetWait) return; 
  
  const dataWait = sheetWait.getDataRange().getValues();
  const sheetUsers = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_USERS); 
  const dataUsers = sheetUsers.getDataRange().getValues();
  const headers = dataUsers[0]; 
  const emailColIdx = headers.indexOf('Email'); 
  
  if (emailColIdx === -1) return;
  
  let notifiedIds = []; 
  let rowsToDelete = [];
  
  for (let i = dataWait.length - 1; i >= 1; i--) {
     let wDate = (dataWait[i][3] instanceof Date) ? Utilities.formatDate(dataWait[i][3], Session.getScriptTimeZone(), "yyyy-MM-dd") : String(dataWait[i][3]).trim();
     
     if (dataWait[i][2] === machine && wDate === dateStr && dataWait[i][4] === timeStr) {
        let uId = dataWait[i][1];
        
        if (!notifiedIds.includes(uId)) {
           let uEmail = null; 
           let uName = "";
           
           for(let j = 1; j < dataUsers.length; j++){ 
             if(dataUsers[j][0] === uId) { 
               uEmail = dataUsers[j][emailColIdx]; 
               uName = dataUsers[j][1]; 
               break; 
             } 
           }
           
           if(uEmail && uEmail.includes("@")) {
              const subject = `🟢 แจ้งเตือนคิวหลุด: ${machine} (${dateStr} ${timeStr})`; 
              const body = `เรียนคุณ ${uName},\n\nคิวที่คุณลงชื่อรอไว้ ตอนนี้ "ว่างแล้ว" ครับ!\n\n📌 รายละเอียด:\nเครื่อง: ${machine}\nวันที่: ${dateStr}\nเวลา: ${timeStr}\n\nรีบเข้าไปทำรายการจองผ่าน LINE Bot ได้เลยครับ 🏃‍♂️💨`;
              
              try { 
                MailApp.sendEmail(uEmail, subject, body); 
              } catch(e) { 
                console.log("Email Error: " + e); 
              } 
              
              notifiedIds.push(uId);
           }
        }
        rowsToDelete.push(i + 1);
     }
  }
  
  rowsToDelete.forEach(r => sheetWait.deleteRow(r));
}

function getUserProfileFromSheet(userId) {
  let sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_USERS); 
  let data = sheet.getDataRange().getValues(); 
  let headers = data[0];
  let emailColIdx = headers.indexOf('Email'); 
  let phoneColIdx = headers.indexOf('Phone');
  
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === userId) {
      let rawDate = data[i][4]; 
      let dateDisplay = (rawDate instanceof Date) ? Utilities.formatDate(rawDate, "GMT+7", "dd/MM/yyyy HH:mm") : String(rawDate);
      let status = (data[i][5] !== undefined && data[i][5] !== "") ? String(data[i][5]).trim() : "Active";
      let email = (emailColIdx !== -1 && data[i][emailColIdx]) ? String(data[i][emailColIdx]).trim() : "";
      let phone = (phoneColIdx !== -1 && data[i][phoneColIdx]) ? String(data[i][phoneColIdx]).trim() : "";
      
      return { 
        name: data[i][1], 
        year: data[i][2], 
        advisor: data[i][3], 
        date: dateDisplay, 
        status: status, 
        email: email, 
        phone: phone 
      };
    }
  } 
  return null;
}

function replyUserProfile(replyToken, profile) {
  let statusText = profile.status === "Active" ? "🟢 ปกติ" : profile.status === "Banned" ? "🔴 ระงับสิทธิ์" : "⏳ รออนุมัติ";
  
  let flex = {
    "type": "bubble",
    "header": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.HEADER_BG,
      "contents": [{ "type": "text", "text": "ข้อมูลสมาชิก", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg" }]
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        {
          "type": "box",
          "layout": "vertical",
          "margin": "md",
          "spacing": "sm",
          "contents": [
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Name:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": profile.name, "wrap": true, "color": COLOR_THEME.TEXT_MAIN, "size": "sm", "flex": 5 } ] },
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Year:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": profile.year, "wrap": true, "color": COLOR_THEME.TEXT_MAIN, "size": "sm", "flex": 5 } ] },
            { "type": "box", "layout": "baseline", "contents": [ { "type": "text", "text": "Status:", "color": COLOR_THEME.TEXT_SUB, "size": "sm", "flex": 2 }, { "type": "text", "text": statusText, "weight": "bold", "color": (profile.status === "Active" ? "#4ADE80" : "#FF5555"), "size": "sm", "flex": 5 } ] }
          ]
        },
        { "type": "separator", "margin": "md", "color": "#555555" },
        { "type": "text", "text": "Regis Date: " + profile.date, "size": "xs", "color": COLOR_THEME.TEXT_SUB, "margin": "md", "align": "end" }
      ]
    },
    "footer": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [
        { "type": "button", "style": "primary", "color": COLOR_THEME.BUTTON_OK, "action": { "type": "message", "label": "จองเครื่องมือ", "text": "จองเครื่องมือ" } }
      ]
    }
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
    sendLineReply(replyToken, [{ type: "text", text: "📭 ไม่มีประวัติการจอง" }]); 
    return; 
  }
  
  myHistory.sort((a, b) => b.timestamp - a.timestamp);
  
  let historyRows = myHistory.slice(0, 10).map(item => ({
    "type": "box",
    "layout": "vertical",
    "margin": "md",
    "contents": [
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          { "type": "text", "text": item.date, "color": COLOR_THEME.TEXT_SUB, "size": "xs", "flex": 2 },
          { "type": "text", "text": item.machine, "color": COLOR_THEME.TEXT_MAIN, "weight": "bold", "size": "sm", "flex": 4 },
          { "type": "text", "text": item.time, "color": COLOR_THEME.BUTTON_OK, "size": "xs", "align": "end", "flex": 3 }
        ]
      },
      { "type": "separator", "margin": "sm", "color": "#444444" }
    ]
  }));
  
  let flex = {
    "type": "bubble",
    "header": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.HEADER_BG,
      "contents": [ { "type": "text", "text": "ประวัติล่าสุด", "weight": "bold", "color": COLOR_THEME.TEXT_MAIN, "size": "lg" } ]
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": COLOR_THEME.BODY_BG,
      "contents": [ ...historyRows ]
    }
  };
  
  sendLineReply(replyToken, [{ "type": "flex", "altText": "History", "contents": flex }]);
}

function clearCache(userId) { 
  const cache = CacheService.getScriptCache(); 
  cache.removeAll(["state_" + userId, "cart_" + userId, "temp_name_" + userId, "temp_year_" + userId, "temp_adv_" + userId, "temp_email_" + userId, "is_update_" + userId, "wait_" + userId]); 
}

function sendLineReply(replyToken, messages) { 
  UrlFetchApp.fetch('https://api.line.me/v2/bot/message/reply', { 
    'headers': { 
      'Content-Type': 'application/json', 
      'Authorization': 'Bearer ' + CHANNEL_ACCESS_TOKEN 
    }, 
    'method': 'post', 
    'payload': JSON.stringify({ 'replyToken': replyToken, 'messages': messages }) 
  }); 
}

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

function markDataChanged() { 
  PropertiesService.getScriptProperties().setProperty('LAST_UPDATE', new Date().getTime()); 
}

function getLastUpdateTimestamp() { 
  return PropertiesService.getScriptProperties().getProperty('LAST_UPDATE') || 0; 
}