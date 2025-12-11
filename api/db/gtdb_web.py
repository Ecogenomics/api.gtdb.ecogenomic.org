from sqlmodel import Field, SQLModel, Column, CHAR, JSON

"""
Tables below.
"""


class DbGenomeTaxId(SQLModel, table=True):
    __tablename__ = 'genome_taxid'

    genome_id: str = Field(primary_key=True)
    payload: dict | None = Field(sa_column=Column(JSON, nullable=True))


class DbGtdbTaxaNotInLit(SQLModel, table=True):
    __tablename__ = 'gtdb_taxa_not_in_lit'

    taxon: str = Field(primary_key=True)
    gtdb_domain: str = Field()
    gtdb_phylum: str = Field()
    gtdb_class: str | None = Field()
    gtdb_order: str | None = Field()
    gtdb_family: str | None = Field()
    gtdb_genus: str | None = Field()
    gtdb_species: str | None = Field()
    appeared_in_release: str = Field()
    taxon_status: str = Field()
    notes: str = Field()


class DbGtdbTree(SQLModel, table=True):
    __tablename__ = 'gtdb_tree'

    id: int | None = Field(primary_key=True, default=None)
    taxon: str = Field()
    total: int = Field()
    type: str = Field()
    is_rep: bool | None = Field()
    type_material: str | None = Field()
    n_desc_children: int | None = Field()


class DbGtdbTreeChildren(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_children'

    parent_id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    child_id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    order_id: int = Field()


class DbGtdbTreeUrlBergeys(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_url_bergeys'

    id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    url: str = Field()


class DbGtdbTreeUrlLpsn(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_url_lpsn'

    id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    url: str = Field()


class DbGtdbTreeUrlNcbi(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_url_ncbi'

    id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    taxid: int = Field()


class DbGtdbTreeUrlSandpiper(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_url_sandpiper'

    id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    url: str = Field()


class DbGtdbTreeUrlSeqCode(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_url_seqcode'

    id: int = Field(primary_key=True, foreign_key='gtdb_tree.id')
    url: str = Field()


class DbLpsnUrl(SQLModel, table=True):
    __tablename__ = 'lpsn_url'

    gtdb_species: str = Field(primary_key=True)
    lpsn_url: str = Field()


class DbTaxonHist(SQLModel, table=True):
    __tablename__ = 'taxon_hist'

    release_ver: str = Field(sa_column=Column(CHAR(5), primary_key=True))
    genome_id: str = Field(sa_column=Column(CHAR(10), primary_key=True))
    rank_domain: str = Field()
    rank_phylum: str = Field()
    rank_class: str = Field()
    rank_order: str = Field()
    rank_family: str = Field()
    rank_genus: str = Field()
    rank_species: str = Field()


class DbUbaAlias(SQLModel, table=True):
    __tablename__ = 'uba_alias'

    id: int | None = Field(primary_key=True, default=None)
    u_accession: str = Field()
    uba_accession: str = Field()
    ncbi_accession: str | None = Field()


"""
Materialized views below.
"""


class DbTaxonHistoryMtView(SQLModel, table=True):
    __tablename__ = 'taxon_history_mtview'

    genome_id: int = Field(primary_key=True)
    R80: str | None = Field()
    R83: str | None = Field()
    R86_2: str | None = Field(sa_column=Column(name='R86.2'))
    R89: str | None = Field()
    R95: str | None = Field()
    R202: str | None = Field()
    R207: str | None = Field()
    R214: str | None = Field()
    R220: str | None = Field()
    R226: str | None = Field()
    NCBI: str | None = Field()


"""
Views below.
"""
