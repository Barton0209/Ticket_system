cd 'C:\OCR_BEST\Ticket_system'
git init
git add .
git commit -m "Add project files"

# добавить remote (замените URL)
git remote add origin https://github.com/YOUR_USERNAME/EXISTING_REPO.git

# получить данные с удалённого
git fetch origin

# если удалённая ветка пуста — можно сразу пушить:
# git push -u origin main

# если в удалённой ветке есть история — подтяните и сделайте ребейз/слияние:
git pull --rebase origin main
# или, если предпочитаете merge:
# git pull origin main

# разрешите возможные конфликты, затем:
git push -u origin main