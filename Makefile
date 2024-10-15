MANAGE = python manage.py

# List of fixtures in the correct loading order
FIXTURES = \
    apps/security/fixtures/user-fixture.csv:security.User \
    apps/talent/fixtures/person-fixture.csv:talent.Person \
    apps/talent/fixtures/skill-fixture.csv:talent.Skill \
    apps/talent/fixtures/expertise-fixture.csv:talent.Expertise \
    apps/talent/fixtures/person-skill-fixture.csv:talent.PersonSkill \
    apps/commerce/fixtures/organisation-fixture.csv:commerce.Organisation \
    apps/product_management/fixtures/product-fixture.csv:product_management.Product \
    apps/product_management/fixtures/product-tree-fixture.csv:product_management.ProductTree \
    apps/product_management/fixtures/product-area-fixture.csv:product_management.ProductArea \
    apps/commerce/fixtures/organisation-point-account-fixture.csv:commerce.OrganisationPointAccount \
    apps/commerce/fixtures/product-point-account-fixture.csv:commerce.ProductPointAccount \
    apps/commerce/fixtures/platform-fee-configuration-fixture.csv:commerce.PlatformFeeConfiguration \
    apps/product_management/fixtures/initiative-fixture.csv:product_management.Initiative \
    apps/product_management/fixtures/challenge-fixture.csv:product_management.Challenge \
    apps/product_management/fixtures/competition-fixture.csv:product_management.Competition \
    apps/product_management/fixtures/bounty-fixture.csv:product_management.Bounty \
	apps/product_management/fixtures/bounty-skill-fixture.csv:product_management.BountySkill \
    apps/talent/fixtures/bounty-bid-fixture.csv:talent.BountyBid \
    apps/talent/fixtures/bounty-claim-fixture.csv:talent.BountyClaim \
    apps/talent/fixtures/bounty-delivery-attempt-fixture.csv:talent.BountyDeliveryAttempt \
    apps/commerce/fixtures/cart-fixture.csv:commerce.Cart \
    apps/commerce/fixtures/cart-line-item-fixture.csv:commerce.CartLineItem \
    apps/commerce/fixtures/sales-order-fixture.csv:commerce.SalesOrder \
    apps/commerce/fixtures/sales-order-line-item-fixture.csv:commerce.SalesOrderLineItem \
    apps/commerce/fixtures/point-transaction-fixture.csv:commerce.PointTransaction \
    apps/commerce/fixtures/point-order-fixture.csv:commerce.PointOrder \
    apps/product_management/fixtures/competition-entry-fixture.csv:product_management.CompetitionEntry \
    apps/product_management/fixtures/competition-entry-rating-fixture.csv:product_management.CompetitionEntryRating \
    apps/product_management/fixtures/contributor-guide-fixture.csv:product_management.ContributorGuide \
    apps/product_management/fixtures/file-attachment-fixture.csv:product_management.FileAttachment \
    apps/product_management/fixtures/idea-fixture.csv:product_management.Idea \
    apps/product_management/fixtures/idea-vote-fixture.csv:product_management.IdeaVote \
    apps/product_management/fixtures/product-contributor-agreement-template-fixture.csv:product_management.ProductContributorAgreementTemplate \
    apps/product_management/fixtures/product-contributor-agreement-fixture.csv:product_management.ProductContributorAgreement \
    apps/product_management/fixtures/bug-fixture.csv:product_management.Bug \
    apps/commerce/fixtures/organisation-point-grant-fixture.csv:commerce.OrganisationPointGrant \
    apps/security/fixtures/organisation-person-role-assignment-fixture.csv:security.OrganisationPersonRoleAssignment \
    apps/security/fixtures/product-role-assignment-fixture.csv:security.ProductRoleAssignment \
    apps/security/fixtures/sign-in-attempt-fixture.csv:security.SignInAttempt \
    apps/security/fixtures/sign-up-request-fixture.csv:security.SignUpRequest \
    apps/engagement/fixtures/email-notification-fixture.csv:engagement.EmailNotification

help:
	@echo "help               -- Print this help showing all commands.         "
	@echo "run                -- run the django development server             "
	@echo "test               -- run all tests                                 "
	@echo "cov                -- run all tests with coverage                   "
	@echo "cov_html           -- run all tests with html coverage              "
	@echo "migrate            -- prepare migrations and migrate                "
	@echo "admin              -- Created superuser and it prompt for password  "
	@echo "seed               -- Seed or load data from each app		 	   "
	@echo "setup              -- load all the data from the fixture to the app "
	@echo "dumpdata           -- Backup the data from the running django app   "
	@echo "tailwindcss        -- Generate Tailwindcss 						   "

rmpyc:
	find . | grep -E "__pycache__|\.pyc|\.pyo" | xargs sudo rm -rf

run:
	$(MANAGE) runserver

migrate:
	$(MANAGE) makemigrations
	$(MANAGE) migrate

seed:
	@echo "Starting seed process"
	@echo "Recreating database"
	python reset_database.py
	@echo "Running migrations"
	make migrate
	@echo "Loading fixtures"
	for fixture in $(FIXTURES); do \
		file=$$(echo $$fixture | cut -d: -f1); \
		model=$$(echo $$fixture | cut -d: -f2); \
		echo "Running command: ${MANAGE} loadcsv $$file --model $$model"; \
		${MANAGE} loadcsv $$file --model $$model || exit 1; \
	done

setup:
	python reset_database.py
	make migrate

full_setup:
	python reset_database.py
	make migrate
	make seed
	make test

dumpdata:
	${MANAGE} dumpdata canopy --output apps/canopy/fixtures/canopy.json
	${MANAGE} dumpdata commerce --output apps/commerce/fixtures/commerce.json
	${MANAGE} dumpdata engagement --output apps/engagement/fixtures/engagement.json
	${MANAGE} dumpdata product_management --output apps/product_management/fixtures/product_management.json
	${MANAGE} dumpdata security --output apps/security/fixtures/security.json
	${MANAGE} dumpdata talent --output apps/talent/fixtures/talent.json
	make format_fixtures

admin:
	$(MANAGE) createsuperuser --username=admin --email=admin@gmail.com

test:
	pytest .

tailwindcss:
	tailwindcss -o ./static/styles/tailwind.css --minify

format_fixtures:
	jsonformat 	apps/canopy/fixtures/canopy.json
	jsonformat	apps/commerce/fixtures/commerce.json
	jsonformat	apps/engagement/fixtures/engagement.json
	jsonformat	apps/product_management/fixtures/product_management.json
	jsonformat	apps/security/fixtures/security.json
	jsonformat	apps/talent/fixtures/talent.json

cov:
	pytest --cov

cov_html:
	pytest --cov  --cov-report html --cov-fail-under=50
