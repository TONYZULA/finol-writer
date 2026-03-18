# WordPress Integration Setup Guide

## 🔧 WordPress Configuration

### Step 1: Enable REST API

WordPress REST API should be enabled by default. To verify:

1. Visit: `https://your-site.com/wp-json/wp/v2/posts`
2. You should see JSON data (not an error)
3. If you see an error, contact your hosting provider

### Step 2: Create Application Password

**Important:** Use Application Password, NOT your regular WordPress password!

1. Log into WordPress Admin
2. Go to **Users** → **Profile**
3. Scroll down to **Application Passwords** section
4. Enter a name (e.g., "FINOL Blog Writer")
5. Click **Add New Application Password**
6. **Copy the generated password** (you won't see it again!)
7. Use this password in the Streamlit app

**Example Application Password:**
```
xxxx xxxx xxxx xxxx xxxx xxxx
```

### Step 3: Verify User Permissions

Your WordPress user must have:
- ✅ **publish_posts** capability
- ✅ **upload_files** capability
- ✅ **edit_posts** capability

Usually, **Administrator** or **Editor** roles have these permissions.

---

## 📝 Using in Streamlit App

### Enter Credentials in Sidebar

1. **WP URL**: Full WordPress site URL
   - ✅ Good: `https://yourblog.com`
   - ✅ Good: `https://yourblog.com/blog`
   - ❌ Bad: `yourblog.com` (missing https://)
   - ❌ Bad: `https://yourblog.com/` (trailing slash is OK but not needed)

2. **WP Username**: Your WordPress username
   - ✅ Good: `admin`
   - ✅ Good: `john.doe`
   - ❌ Bad: Email address (use username, not email)

3. **WP App Password**: Application Password (from Step 2)
   - ✅ Good: `xxxx xxxx xxxx xxxx xxxx xxxx`
   - ❌ Bad: Your regular WordPress password

---

## 🐛 Common Issues & Solutions

### Issue 1: "Publishing failed" - JSON Decode Error

**Error:**
```
RequestsJSONDecodeError: Expecting value
```

**Causes:**
- WordPress returned HTML instead of JSON
- REST API is disabled
- Authentication failed
- URL is incorrect

**Solutions:**
1. ✅ **Fixed in latest code** - App now handles non-JSON responses
2. Verify REST API is accessible: `https://your-site.com/wp-json/wp/v2/posts`
3. Check WordPress URL is correct
4. Verify Application Password is correct
5. Reboot Streamlit app to get the fix

---

### Issue 2: "Media upload failed"

**Error:**
```
Media upload failed: 401 - Unauthorized
```

**Causes:**
- Wrong Application Password
- User doesn't have upload_files permission
- REST API authentication issue

**Solutions:**
1. Regenerate Application Password
2. Verify user is Administrator or Editor
3. Check WordPress REST API authentication settings
4. Try uploading manually to verify permissions

**Note:** App will continue without featured image if upload fails

---

### Issue 3: "Post creation failed: 401"

**Error:**
```
Post creation failed: 401 - Unauthorized
```

**Causes:**
- Wrong credentials
- User doesn't have publish_posts permission
- Application Password expired or revoked

**Solutions:**
1. Verify username is correct (not email)
2. Create new Application Password
3. Check user role (should be Administrator or Editor)
4. Test credentials with REST API directly

---

### Issue 4: "Post creation failed: 403"

**Error:**
```
Post creation failed: 403 - Forbidden
```

**Causes:**
- User lacks publishing permissions
- WordPress security plugin blocking REST API
- Server firewall blocking requests

**Solutions:**
1. Check user role and permissions
2. Temporarily disable security plugins
3. Check WordPress security settings
4. Contact hosting provider about REST API access

---

### Issue 5: REST API Not Accessible

**Symptom:** Can't access `https://your-site.com/wp-json/`

**Causes:**
- Permalink structure not set
- REST API disabled by plugin
- Server configuration issue

**Solutions:**
1. Go to **Settings** → **Permalinks**
2. Select any option except "Plain"
3. Click **Save Changes**
4. Disable any plugins that might block REST API
5. Check `.htaccess` file for REST API blocks

---

### Issue 6: "Cover image upload failed"

**Symptom:** Post publishes but without featured image

**Causes:**
- Templated API key missing or invalid
- Image generation failed
- Media upload permissions issue

**Solutions:**
1. Verify `TEMPLATED_API_KEY` in Streamlit Secrets
2. Check Templated.io account has quota
3. Verify WordPress user can upload media
4. Post will still publish without image (by design)

---

## ✅ Testing WordPress Integration

### Test 1: Verify REST API Access

```bash
# Test posts endpoint
curl https://your-site.com/wp-json/wp/v2/posts

# Should return JSON with posts list
```

### Test 2: Test Authentication

```bash
# Replace with your credentials
curl -X POST https://your-site.com/wp-json/wp/v2/posts \
  -u "username:xxxx xxxx xxxx xxxx xxxx xxxx" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Post","content":"Test content","status":"draft"}'

# Should return JSON with created post
```

### Test 3: Test in Streamlit App

1. Generate a test article
2. Fill in WordPress credentials
3. Click "Publish to WordPress"
4. Check for success message
5. Verify post appears in WordPress

---

## 🔐 Security Best Practices

### 1. Use Application Passwords
- ✅ Never use your main WordPress password
- ✅ Create separate Application Password for each app
- ✅ Revoke unused Application Passwords regularly

### 2. Limit User Permissions
- ✅ Use Editor role if possible (not Administrator)
- ✅ Only grant necessary permissions
- ✅ Review user capabilities regularly

### 3. Secure Your WordPress Site
- ✅ Use HTTPS (SSL certificate)
- ✅ Keep WordPress updated
- ✅ Use security plugins (but allow REST API)
- ✅ Enable two-factor authentication

### 4. Monitor API Usage
- ✅ Check WordPress logs for API requests
- ✅ Revoke suspicious Application Passwords
- ✅ Monitor for unauthorized posts

---

## 📊 WordPress REST API Endpoints Used

### 1. Media Upload
```
POST /wp-json/wp/v2/media
Content-Type: image/jpeg
Authorization: Basic (username:app_password)
```

### 2. Post Creation
```
POST /wp-json/wp/v2/posts
Content-Type: application/json
Authorization: Basic (username:app_password)

Body:
{
  "title": "Post Title",
  "content": "Post content in HTML/Markdown",
  "status": "publish",
  "featured_media": 123  // Optional, media ID
}
```

---

## 🎯 Troubleshooting Checklist

Before publishing, verify:

- [ ] WordPress URL is correct (with https://)
- [ ] Username is correct (not email)
- [ ] Using Application Password (not regular password)
- [ ] REST API is accessible
- [ ] User has publishing permissions
- [ ] WordPress site is online and accessible
- [ ] No security plugins blocking REST API
- [ ] Permalink structure is set (not "Plain")

---

## 💡 Pro Tips

### 1. Test with Draft First
Change status to "draft" in code to test without publishing:
```python
payload = {
    "title": title,
    "content": content,
    "status": "draft"  # Change to "draft" for testing
}
```

### 2. Use Staging Site
Test on a staging WordPress site before production.

### 3. Check WordPress Logs
Enable WordPress debug logging to see API errors:
```php
// In wp-config.php
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
```

### 4. Backup Before Testing
Always backup WordPress before testing integrations.

---

## 🆘 Still Having Issues?

### Check WordPress Documentation
- [REST API Handbook](https://developer.wordpress.org/rest-api/)
- [Application Passwords](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/)

### Check Hosting Provider
Some hosts restrict REST API access. Contact support if:
- REST API returns 403 or 404
- Can't access /wp-json/ endpoints
- Authentication always fails

### Test Locally
Try publishing to a local WordPress installation to isolate issues.

---

## ✅ Success Indicators

Publishing is working when:

✅ No error messages in Streamlit
✅ Success message with post link appears
✅ Post appears in WordPress admin
✅ Post is published (not draft)
✅ Featured image is set (if upload succeeded)
✅ Content is formatted correctly

---

**Latest code includes robust error handling for WordPress integration!** 🎉
