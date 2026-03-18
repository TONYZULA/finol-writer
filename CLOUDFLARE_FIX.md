# Cloudflare 403 Error Fix

## 🚨 Problem

**Error:** `403 - <!DOCTYPE html><html lang="en-US"><head><title>Just a moment...`

This is **Cloudflare's bot protection** blocking Streamlit Cloud's requests to your WordPress site.

---

## ✅ Solutions (Choose One)

### Solution 1: Whitelist Streamlit Cloud IPs (Recommended)

**In Cloudflare Dashboard:**

1. Log into [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. Go to **Security** → **WAF** (Web Application Firewall)
4. Click **Tools**
5. Click **IP Access Rules**
6. Add these Streamlit Cloud IP ranges:

```
# Streamlit Cloud IP ranges (add all)
35.160.0.0/13
52.32.0.0/14
54.68.0.0/14
```

7. Set Action: **Allow**
8. Click **Add**

---

### Solution 2: Disable Bot Fight Mode for REST API

**In Cloudflare Dashboard:**

1. Go to **Security** → **Bots**
2. Find **Bot Fight Mode**
3. Click **Configure**
4. Add exception for `/wp-json/*` path
5. Save changes

**Or create a Page Rule:**

1. Go to **Rules** → **Page Rules**
2. Click **Create Page Rule**
3. URL pattern: `yourdomain.com/wp-json/*`
4. Setting: **Security Level** → **Essentially Off**
5. Save and Deploy

---

### Solution 3: Create Firewall Rule to Allow REST API

**In Cloudflare Dashboard:**

1. Go to **Security** → **WAF**
2. Click **Create rule**
3. Rule name: `Allow WordPress REST API`
4. Expression:
```
(http.request.uri.path contains "/wp-json/")
```
5. Action: **Allow**
6. Deploy

---

### Solution 4: Use Cloudflare API Token (Advanced)

**Create a bypass token:**

1. Cloudflare Dashboard → **My Profile** → **API Tokens**
2. Create token with **Zone.Zone** read permissions
3. Add to requests as header:
```python
headers = {
    "Authorization": f"Bearer {cloudflare_token}",
    "CF-Access-Client-Id": "your-client-id",
    "CF-Access-Client-Secret": "your-client-secret"
}
```

---

### Solution 5: Temporary - Lower Security Level

**Quick test (not recommended for production):**

1. Cloudflare Dashboard → **Security** → **Settings**
2. **Security Level** → Change to **Low** or **Essentially Off**
3. Test publishing
4. **Remember to change back to High after testing!**

---

## 🔧 Alternative: Use WordPress Plugin

### Install "Cloudflare Flexible SSL" Plugin

1. WordPress Admin → **Plugins** → **Add New**
2. Search: "Cloudflare"
3. Install **Cloudflare** official plugin
4. Activate and configure with your Cloudflare API key
5. This helps WordPress work better with Cloudflare

---

## 🎯 Recommended Approach

### Best Practice (Most Secure):

1. **Create Firewall Rule** (Solution 3) to allow `/wp-json/*`
2. **Keep Bot Fight Mode** enabled for other paths
3. **Monitor logs** to ensure no abuse

This allows REST API access while keeping your site protected.

---

## 🧪 Testing After Fix

### Test 1: Check REST API Access

```bash
# Should return JSON, not HTML
curl https://yourdomain.com/wp-json/wp/v2/posts
```

If you see JSON → ✅ Fixed!
If you see HTML with "Just a moment" → ❌ Still blocked

### Test 2: Test with Authentication

```bash
curl -X POST https://yourdomain.com/wp-json/wp/v2/posts \
  -u "username:app_password" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Test","status":"draft"}'
```

Should return JSON with created post.

### Test 3: Test in Streamlit App

1. Apply Cloudflare fix
2. Wait 2-3 minutes for changes to propagate
3. Try publishing from Streamlit app
4. Should work without 403 error

---

## 🔍 How to Identify Cloudflare Blocking

**Signs of Cloudflare blocking:**
- ✅ Error contains "Just a moment..."
- ✅ Error shows HTML instead of JSON
- ✅ Status code is 403 or 503
- ✅ Response contains Cloudflare branding
- ✅ Works in browser but not from API

**Not Cloudflare if:**
- ❌ Error is pure JSON
- ❌ Status code is 401 (authentication)
- ❌ Error mentions WordPress specifically
- ❌ No HTML in response

---

## 📊 Why This Happens

### Cloudflare's Perspective:
```
Streamlit Cloud request → Looks like a bot → Block it
```

### What Cloudflare Sees:
- Automated requests (not from browser)
- No JavaScript execution
- No cookies/session
- Rapid requests
- Non-standard User-Agent

### Solution:
Tell Cloudflare: "This bot is OK, it's my app!"

---

## 🚀 Quick Fix for Testing

**If you need to test immediately:**

1. **Temporarily disable Cloudflare proxy:**
   - Cloudflare Dashboard → **DNS**
   - Find your domain's A record
   - Click the orange cloud (make it gray)
   - Wait 5 minutes
   - Test publishing
   - **Re-enable proxy after testing!**

2. **Or use direct server IP:**
   - Find your server's IP address
   - Add to `/etc/hosts` locally
   - Test from local machine
   - Not possible from Streamlit Cloud

---

## 💡 Long-Term Solution

### Recommended Setup:

1. **Cloudflare Firewall Rule** (Solution 3)
   - Allows `/wp-json/*` path
   - Keeps protection on other paths
   - No security compromise

2. **Monitor Access Logs**
   - Check for abuse
   - Review API usage
   - Block suspicious IPs if needed

3. **Rate Limiting** (Optional)
   - Cloudflare → **Security** → **Rate Limiting**
   - Limit requests to `/wp-json/*`
   - Prevents abuse while allowing legitimate use

---

## 🆘 Still Not Working?

### Check These:

1. **Cloudflare changes take time**
   - Wait 2-5 minutes after making changes
   - Clear Cloudflare cache if needed

2. **Multiple Cloudflare rules**
   - Check all firewall rules
   - Ensure no conflicting rules
   - Order matters (first match wins)

3. **WordPress security plugins**
   - Wordfence, iThemes Security, etc.
   - May have their own blocking
   - Check plugin logs

4. **Server firewall**
   - Some hosts have additional firewalls
   - Contact hosting support
   - Ask to whitelist Streamlit Cloud IPs

---

## 📞 Need Help?

### Cloudflare Support
- [Cloudflare Community](https://community.cloudflare.com)
- [Cloudflare Docs](https://developers.cloudflare.com)

### WordPress + Cloudflare
- [WordPress REST API + Cloudflare Guide](https://wordpress.org/support/article/rest-api/)

---

## ✅ Success Checklist

After applying fix:

- [ ] Cloudflare firewall rule created
- [ ] Waited 2-5 minutes for propagation
- [ ] Tested REST API with curl (returns JSON)
- [ ] Tested authentication (returns JSON)
- [ ] Tested in Streamlit app (publishes successfully)
- [ ] No 403 errors
- [ ] Post appears in WordPress

---

**Most common solution: Create Cloudflare Firewall Rule to allow `/wp-json/*` path** ✅
