# требуется установленный gh и аутентификация (gh auth login)
cd 'C:\OCR_BEST\Ticket_system'
gh repo create REPO_NAME --public --source=. --remote=origin --push
# для приватного: замените --public на --private