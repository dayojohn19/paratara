# Quick Deployment Checklist for Heroku

## ✅ Pre-Deployment

- [ ] All changes committed to git
- [ ] Environment variables configured on Heroku
- [ ] Redis addon added (optional but recommended)
- [ ] Database backup created

## 🚀 Deployment Commands

```bash
# 1. Add and commit all optimization changes
git add .
git commit -m "Optimize project for Heroku deployment"

# 2. Set environment variables (if not already set)
heroku config:set DEBUG=False
heroku config:set SECRET_KEY='your-secret-key-generate-a-new-one'

# 3. Optional: Add Redis for caching (HIGHLY RECOMMENDED)
heroku addons:create heroku-redis:mini

# 4. Deploy to Heroku
git push heroku main

# 5. Run migrations
heroku run python manage.py migrate

# 6. Collect static files (should be automatic but verify)
heroku run python manage.py collectstatic --noinput

# 7. Restart dynos to apply all settings
heroku restart

# 8. Check logs
heroku logs --tail
```

## 🔍 Verify Deployment

```bash
# Check if app is running
heroku ps

# Test the application
curl -I https://your-app.herokuapp.com

# Monitor logs for errors
heroku logs --tail --source app

# Check Redis connection (if using Redis)
heroku redis:info
```

## ⚡ Performance Settings

### Dyno Configuration (Edit in Heroku Dashboard or CLI)

```bash
# Upgrade to Performance or Professional dynos for better performance
# Standard-1X: Basic ($25/month)
# Standard-2X: Better performance ($50/month)

heroku ps:scale web=1:standard-1x
```

### Environment Variables to Set

```bash
# Required
heroku config:set DEBUG=False
heroku config:set SECRET_KEY='generate-a-long-random-string'

# Optional but recommended
heroku config:set DJANGO_SETTINGS_MODULE='webSchedule.settings'
heroku config:set WEB_CONCURRENCY=4

# If using external services
heroku config:set OPENAI_API_KEY='your-key'
heroku config:set IMGBB_API_KEY='your-key'
heroku config:set PAYPAL_CLIENT_ID='your-id'
heroku config:set PAYPAL_SECRET='your-secret'
```

## 📊 Expected Results

After deployment, you should see:

1. ✅ Faster page load times (40-60% improvement)
2. ✅ Reduced database query time
3. ✅ Compressed static files (smaller transfer size)
4. ✅ Better handling of concurrent requests
5. ✅ Faster build times

## 🐛 Troubleshooting

### If deployment fails:

```bash
# Check build logs
heroku logs --tail --source app

# Verify Python version
heroku run python --version

# Check installed packages
heroku run pip list

# Test settings
heroku run python manage.py check --deploy
```

### If app is slow after deployment:

```bash
# Check dyno metrics
heroku ps

# Add Redis if not already added
heroku addons:create heroku-redis:mini

# Scale up dynos
heroku ps:scale web=2

# Check for slow queries in logs
heroku logs --tail | grep "Slow"
```

### If static files not loading:

```bash
# Manually collect static files
heroku run python manage.py collectstatic --noinput

# Verify STATIC_URL setting
heroku run python manage.py shell
>>> from django.conf import settings
>>> print(settings.STATIC_URL)
>>> print(settings.STATIC_ROOT)
```

## 📈 Monitoring

### View real-time metrics:

1. Go to Heroku Dashboard
2. Select your app
3. Go to "Metrics" tab
4. Monitor:
   - Response time
   - Throughput
   - Memory usage
   - Error rate

### Or use CLI:

```bash
# View recent errors
heroku logs --tail --level error

# View app info
heroku info

# View recent releases
heroku releases
```

## 🎯 Post-Deployment Optimization

After successful deployment, consider:

1. **Add CDN** for static files (Cloudflare, AWS CloudFront)
2. **Enable Auto-scaling** if traffic varies
3. **Add New Relic** or similar APM tool
4. **Set up monitoring alerts**
5. **Schedule regular database maintenance**

## 💰 Cost Optimization

```bash
# Check current dyno usage
heroku ps

# Optimize dyno usage
heroku ps:scale web=1  # Use 1 dyno if low traffic

# Check addon costs
heroku addons

# Heroku Redis Mini: $3/month (totally worth it!)
```

## 🔄 Rollback if Needed

```bash
# List recent releases
heroku releases

# Rollback to previous version
heroku rollback v[version-number]

# Example: rollback to version 10
heroku rollback v10
```

## ✨ All Done!

Your app is now optimized and deployed to Heroku! 🎉

Test it at: https://your-app.herokuapp.com
