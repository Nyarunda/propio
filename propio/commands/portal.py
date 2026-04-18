from __future__ import unicode_literals

import click
import frappe
from frappe.commands import pass_context
from frappe.exceptions import SiteNotSpecifiedError

from propio.portal_utils.tenant_provisioning import create_tenant_portal_access, provision_all_tenants_with_email


def _iter_sites(context):
    if not context.sites:
        raise SiteNotSpecifiedError
    return context.sites


@click.command("provision-tenant-portal")
@click.argument("tenant")
@click.option("--email", default=None, help="Email address for portal access")
@click.option("--no-welcome", is_flag=True, default=False, help="Do not send welcome email")
@pass_context
def provision_tenant_portal(context, tenant, email=None, no_welcome=False):
    """Provision portal access for a single tenant."""
    for site in _iter_sites(context):
        try:
            frappe.init(site=site)
            frappe.connect()

            result = create_tenant_portal_access(
                tenant_name=tenant,
                email=email,
                send_welcome_email=not no_welcome,
            )
            status = result.get("status")
            prefix = f"[{site}] "
            if status == "success":
                click.secho(f"{prefix}SUCCESS: {result.get('message')}", fg="green")
                if result.get("email"):
                    click.echo(f"{prefix}Email: {result.get('email')}")
                if result.get("temporary_password"):
                    click.secho(f"{prefix}Temporary password: {result.get('temporary_password')}", fg="yellow")
            else:
                click.secho(f"{prefix}ERROR: {result.get('message')}", fg="red")
        finally:
            frappe.destroy()


@click.command("provision-all-tenants")
@click.option("--dry-run", is_flag=True, default=False, help="Show tenants that would be provisioned")
@click.option("--send-welcome", is_flag=True, default=False, help="Send welcome emails")
@pass_context
def provision_all_tenants(context, dry_run=False, send_welcome=False):
    """Provision portal access for all tenants with a primary contact email."""
    for site in _iter_sites(context):
        try:
            frappe.init(site=site)
            frappe.connect()

            tenants = frappe.get_all("Tenant", pluck="name")
            click.echo(f"[{site}] Found {len(tenants)} tenants")

            if dry_run:
                from propio.portal_utils.tenant_provisioning import _tenant_primary_contact_email  # noqa: PLC2701

                for tenant in tenants:
                    email = _tenant_primary_contact_email(tenant)
                    click.echo(f"[{site}] - {tenant}: {email or 'NO PRIMARY EMAIL'}")
                continue

            result = provision_all_tenants_with_email(send_welcome_email=send_welcome)
            click.secho(
                (
                    f"[{site}] Complete: total={result.get('total')} "
                    f"success={result.get('success')} failed={result.get('failed')}"
                ),
                fg="blue",
            )
        finally:
            frappe.destroy()
