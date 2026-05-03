# Useful Links

> 1. ## [reset migration](https://tech.raturi.in/how-reset-django-migrations)
> 2. ## [revert migration](https://stackoverflow.com/questions/32123477/how-to-revert-the-last-migration)
> 3. ## [mongoDB](https://cloud.mongodb.com/v2/6210619e8ad1847d9cfce6b9#/metrics/replicaSet/6210627e540bb978986f10b7/explorer/TreepDB/__schema__/find)
>    `go to migration folder`
> 4. ## [Squash Migration](https://docs.djangoproject.com/en/4.1/topics/migrations/#squashing-migrations)

```
find . -path "*migrations*" -not -regex ".*__init__.py" -a -not -regex ".*migrations" | xargs rm -rf
```

# Sample Output

> python3 manage.py showmigrations

```
social_django
 [X] 0001_initial (2 squashed migrations)
 [ ] 0002_add_related_name (2 squashed migrations)
 [ ] 0003_alter_email_max_length (2 squashed migrations)
 [ ] 0004_auto_20160423_0400 (2 squashed migrations)
 [ ] 0005_auto_20160727_2333 (1 squashed migrations)
 [ ] 0006_partial
 [ ] 0007_code_timestamp
 [ ] 0008_partial_timestamp
```

> python3 manage.py migrate --fake

```
Operations to perform:
  Apply all migrations: admin, apis, auth, contenttypes, home, resorts, sessions, social_django, userProfile
Running migrations:
  Applying admin.0001_initial... FAKED
  Applying admin.0002_logentry_remove_auto_add... FAKED
  Applying admin.0003_logentry_add_action_flag_choices... FAKED
  Applying apis.0002_initial... FAKED
  Applying home.0003_initial... FAKED
```
