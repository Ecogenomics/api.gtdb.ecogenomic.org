import re
import zipfile
from io import BytesIO
from typing import Optional

import dendropy
import requests
import sqlalchemy as sa
from fastapi import UploadFile
from sqlalchemy.orm import Session

from api.config import GTDB_CAPTCHA_SECRET_KEY, Env, ENV_NAME, SMTP_DOMAIN_BLACKLIST
from api.db.models import GtdbWebUbaAlias, Genome
from api.exceptions import HttpBadRequest
from api.model.util import UtilContactEmailRequest, NoUserAccEnum, PrevUserEnum, UserOnlyEnum
from api.util.accession import canonical_gid
from api.util.email import send_smtp_email

RE_CANONICAL = re.compile(r'G\d{9}')
RE_USER = re.compile(r'U_\d+')
RE_UBA = re.compile(r'UBA\d+')


async def send_contact_us_email(request: UtilContactEmailRequest):
    # Validation
    if request.fromEmail is None or not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)",
                                                 request.fromEmail):
        raise HttpBadRequest('Invalid e-mail address')
    if len(request.fromEmail) > 320:
        raise HttpBadRequest('E-mail address is longer than 320 characters.')
    if not request.subject:
        raise HttpBadRequest('You must supply an e-mail subject')
    if not request.message:
        raise HttpBadRequest('You must supply a message')
    if not request.clientResponse:
        raise HttpBadRequest('You must supply the reCAPTCHA token')
    if request.fromEmail.split('@')[1] in SMTP_DOMAIN_BLACKLIST:
        raise HttpBadRequest('E-mail domain has been blacklisted for spamming.')

    # Sanitise the input
    subject = request.subject[0:256]
    message = request.message[0:10000]

    # Verify the reCAPTCHA token
    payload = {
        'secret': GTDB_CAPTCHA_SECRET_KEY,
        'response': request.clientResponse
    }
    endpoint = 'https://www.google.com/recaptcha/api/siteverify'
    r = requests.post(endpoint, data=payload)

    # Send the email
    if r.json().get('success', False) is True:
        if ENV_NAME is Env.PROD:
            to = ["m.chuvochina@gmail.com", "uqpchaum@uq.edu.au",
                  "phugenholtz@gmail.com", "c.rinke@uq.edu.au",
                  "donovan.parks@gmail.com", "a.mussig@uq.edu.au"]
        else:
            to = ["a.mussig@uq.edu.au"]
        subject = f'[GTDB Support] {subject}'
        content = f'From: {request.fromEmail}\n\n' \
                  f'Message:\n{message}'
        await send_smtp_email(content, subject, to)

        # Send confirmation e-mail to user.
        await send_smtp_email(to=[request.fromEmail],
                              content=f'Your message has been sent.\n'
                                      f'Please do not reply to this message, this inbox is not monitored.\n\n'
                                      f'Message:\n{content}',
                              subject='[GTDB Support] Message sent successfully')
        return 'Success!', 200
    else:
        raise HttpBadRequest('Invalid reCAPTCHA response.')


def convert_accession_get_accessions(db):
    out_idx = list()
    out_u = dict()
    out_uba = dict()
    out_ncbi = dict()
    query = sa.select([GtdbWebUbaAlias.u_accession, GtdbWebUbaAlias.uba_accession, GtdbWebUbaAlias.ncbi_accession])
    for idx, row in enumerate(db.execute(query)):
        u_acc, uba_acc, ncbi_acc = row.u_accession, row.uba_accession, row.ncbi_accession
        out_idx.append((u_acc, uba_acc, ncbi_acc))
        out_u[u_acc] = idx
        out_uba[uba_acc] = idx
        if ncbi_acc:
            ncbi_canonical = canonical_gid(ncbi_acc)
            out_ncbi[ncbi_canonical] = idx
    return out_idx, out_u, out_uba, out_ncbi


def canonical_to_short_ncbi(db: Session):
    out = dict()
    query = sa.select([Genome.name])
    for row in db.execute(query):
        # Take the most recent version
        canonical = canonical_gid(row.name)
        if canonical in out:
            existing = out[canonical]
            replace = False
            if existing.startswith('GCF'):
                replace = True
            elif int(existing[-1]) < int(row.name[-1]):
                replace = True
            if replace:
                out[canonical] = row.name
        out[canonical] = row.name
    return out


def convert_tree_accessions(db_web: Session, db_gtdb: Session, noUserAcc: NoUserAccEnum, prevUser: PrevUserEnum,
                            userOnly: UserOnlyEnum, newickFile: Optional[UploadFile] = None,
                            newickString: Optional[str] = None) -> BytesIO:
    MSG_USR_IGNORE = 'Used requested "Do not change"'
    MSG_USR_SAME = 'Accession is already in the desired format'
    MSG_UNKNOWN_OPT = 'Selected option is unknown'
    NO_MAPPING = 'No database mapping for this accession'

    U_COL = 0
    UBA_COL = 1
    NCBI_COL = 2

    # Retrieve the accession mapping from the database
    map_idx, map_u, map_uba, map_ncbi = convert_accession_get_accessions(db_web)

    # Get the canonical to short mapping for ncbi genomes
    map_canonical_to_short = canonical_to_short_ncbi(db_gtdb)

    # Load the form content
    tree_file = newickFile
    tree_text = newickString
    ncbi_radio = noUserAcc
    ncbi_user_radio = prevUser
    user_radio = userOnly

    # Set the newick tree
    if tree_file:
        tree_content = tree_file.file.read().decode()
    else:
        tree_content = tree_text

    # Parse the newick tree
    try:
        tree = dendropy.Tree.get(data=tree_content, schema='newick', preserve_underscores=True)
    except Exception as e:
        raise HttpBadRequest(f'Unable to pass tree: {e}')

    # Log the changes and return them
    out_archive = BytesIO()
    changed_out = list()
    unchanged_out = list()
    novel_out = list()

    def is_long_accession(acc):
        if acc.startswith('GB_GCA'):
            return True
        if acc.startswith('RS_GCF'):
            return True
        return False

    def is_short_accession(acc):
        if acc.startswith('GCA_'):
            return True
        if acc.startswith('GCF_'):
            return True
        return False

    def long_to_short_accession(acc):
        return acc[3:]

    def short_to_long_accession(acc):
        if acc.startswith('GCA'):
            return f'GB_{acc}'
        if acc.startswith('GCF'):
            return f'RS_{acc}'
        return acc

    def is_canonical(acc):
        return RE_CANONICAL.match(acc)

    n_taxa = 0
    for leaf_node in tree.leaf_node_iter():
        n_taxa += 1
        label = leaf_node.taxon.label

        # What type of taxon is this? (ncbi only, user only, or both)
        u_idx = map_u.get(label)
        uba_idx = map_uba.get(label)
        ncbi_idx = map_ncbi.get(canonical_gid(label))
        row_idx = u_idx or uba_idx or ncbi_idx

        # There was a hit to one of the user mapping indexes
        # This is either a ncbi/user or user only genome
        if row_idx:

            # This is a USER only accession (~1400 of these)
            if ncbi_idx is None:
                if user_radio is UserOnlyEnum.IGNORE:
                    unchanged_out.append(f'{label}\tuser_only\t{MSG_USR_IGNORE}')

                elif user_radio is UserOnlyEnum.USER:
                    if RE_USER.match(label):
                        unchanged_out.append(f'{label}\tuser_only\t{MSG_USR_SAME}')
                    else:
                        new_label = map_idx[row_idx][U_COL]
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tuser_only')

                elif user_radio is UserOnlyEnum.UBA:
                    if RE_UBA.match(label):
                        unchanged_out.append(f'{label}\tuser_only\t{MSG_USR_SAME}')
                    else:
                        new_label = map_idx[row_idx][U_COL]
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tuser_only')
                else:
                    unchanged_out.append(f'{label}\tunknown\t{MSG_UNKNOWN_OPT}')

            # This is a NCBI + USER accession
            else:
                if ncbi_user_radio is PrevUserEnum.IGNORE:
                    unchanged_out.append(f'{label}\tncbi_user\t{MSG_USR_IGNORE}')

                elif ncbi_user_radio is PrevUserEnum.USER:
                    if RE_USER.match(label):
                        unchanged_out.append(f'{label}\tncbi_user\t{MSG_USR_SAME}')
                    else:
                        new_label = map_idx[row_idx][U_COL]
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tncbi_user')

                elif ncbi_user_radio is PrevUserEnum.UBA:
                    if RE_UBA.match(label):
                        unchanged_out.append(f'{label}\tncbi_user\t{MSG_USR_SAME}')
                    else:
                        new_label = map_idx[row_idx][UBA_COL]
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tncbi_user')

                elif ncbi_user_radio is PrevUserEnum.LONG:
                    if is_long_accession(label):
                        unchanged_out.append(f'{label}\tncbi_user\t{MSG_USR_SAME}')
                    else:
                        new_label = short_to_long_accession(map_idx[row_idx][NCBI_COL])
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tncbi_user')

                elif ncbi_user_radio is PrevUserEnum.SHORT:
                    if is_short_accession(label):
                        unchanged_out.append(f'{label}\tncbi_user\t{MSG_USR_SAME}')
                    else:
                        new_label = map_idx[row_idx][NCBI_COL]
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tncbi_user')

                elif ncbi_user_radio is PrevUserEnum.CANONICAL:
                    if is_canonical(label):
                        unchanged_out.append(f'{label}\tncbi_user\t{MSG_USR_SAME}')
                    else:
                        new_label = canonical_gid(map_idx[row_idx][NCBI_COL])
                        leaf_node.taxon.label = new_label
                        changed_out.append(f'{label}\t{new_label}\tncbi_user')
                else:
                    unchanged_out.append(f'{label}\tunknown\t{MSG_UNKNOWN_OPT}')

        # This is a NCBI-only genome
        else:
            canonical_acc = canonical_gid(label)
            short_acc = map_canonical_to_short.get(canonical_acc)

            if ncbi_radio is NoUserAccEnum.IGNORE:
                unchanged_out.append(f'{label}\tncbi_only\t{MSG_USR_IGNORE}')

            elif ncbi_radio is NoUserAccEnum.LONG:
                if is_long_accession(label):
                    unchanged_out.append(f'{label}\tncbi_only\t{MSG_USR_SAME}')
                elif is_short_accession(label):
                    new_label = short_to_long_accession(label)
                    leaf_node.taxon.label = new_label
                    changed_out.append(f'{label}\t{new_label}\tncbi_only')
                elif short_acc:
                    new_label = short_to_long_accession(short_acc)
                    leaf_node.taxon.label = new_label
                    changed_out.append(f'{label}\t{new_label}\tncbi_only')
                else:
                    unchanged_out.append(f'{label}\tunknown\t{NO_MAPPING}')

            elif ncbi_radio is NoUserAccEnum.SHORT:
                if is_long_accession(label):
                    new_label = long_to_short_accession(label)
                    leaf_node.taxon.label = new_label
                    changed_out.append(f'{label}\t{new_label}\tncbi_only')
                elif is_short_accession(label):
                    unchanged_out.append(f'{label}\tncbi_only\t{MSG_USR_SAME}')
                elif short_acc:
                    leaf_node.taxon.label = short_acc
                    changed_out.append(f'{label}\t{short_acc}\tncbi_only')
                else:
                    unchanged_out.append(f'{label}\tunknown\t{NO_MAPPING}')

            elif ncbi_radio is NoUserAccEnum.CANONICAL:
                if is_long_accession(label) or is_short_accession(label) or is_canonical(label):
                    if label != canonical_acc:
                        changed_out.append(f'{label}\t{canonical_acc}\tncbi_only')
                        leaf_node.taxon.label = canonical_acc
                    else:
                        unchanged_out.append(f'{label}\tncbi_only\t{MSG_USR_SAME}')
                else:
                    unchanged_out.append(f'{label}\tunknown\t{NO_MAPPING}')

    with zipfile.ZipFile(out_archive, 'w') as zf:

        # Write the modified tree to the zip file
        zf.writestr(tree_file.filename if hasattr(tree_file, 'filename') else 'output.tree',
                    tree.as_string(schema='newick'))
        if len(changed_out) > 0:
            out_str = 'original\tnew\tchange_type\n'
            out_str += '\n'.join(sorted(changed_out))
            zf.writestr('changes_made.tsv', out_str)

        if len(novel_out) > 0:
            zf.writestr('novel_accession.tsv', '\n'.join(sorted(novel_out)))

        if len(unchanged_out) > 0:
            zf.writestr('unchanged_accession.tsv', '\n'.join(sorted(unchanged_out)))

        sanity_file = ('Please always check this file to see if the numbers make sense!\n',
                       f'                TOTAL leaves = {n_taxa:,}',
                       f'                     changed = {len(changed_out):,}',
                       f'                   unchanged = {len(unchanged_out):,}',
                       f'                       novel = {len(novel_out):,}',
                       f'                         SUM = {(len(changed_out) + len(unchanged_out) + len(novel_out)):,}')
        zf.writestr('sanity_check.txt', '\n'.join(sanity_file))

    # Send the parsed tree.
    out_archive.seek(0)
    return out_archive
