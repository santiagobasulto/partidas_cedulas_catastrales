import csv
import itertools
import logging
from pathlib import Path, PosixPath

import click
from colorlog import ColoredFormatter

GLOB = '**/{}*.pdf'

BASE_PATH = '/media/santiago/Nuevo vol/DISTRITO V/'

def setup_logger():
    """Return a logger with a default ColoredFormatter."""
    formatter = ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red',
        }
    )

    logger = logging.getLogger('cedulas')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    return logger


logger = setup_logger()


class RowExtractorException(Exception):
    def __init__(self, filename, path):
        self.filename = filename
        self.path = path


def get_lettered_row_extractor(letter):
    def lettered_row_extractor(file):
        try:
            _, circuns, section, name = file.parts
            number = name[1:name.index(letter)]
            _let = name[name.index(letter)+1:name.index('_')]
            return [name, number, _let, circuns, section, str(file)]
        except:
            logger.exception("ROW EXTRACTOR FAILED FOR FILE: %s", str(file))
            raise RowExtractorException(filename=file.parts[-1], path=str(file))
    return lettered_row_extractor


def simple_row_extractor(file):
    try:
        _, circuns, section, name = file.parts
        return [name, name[1:name.index('_')], circuns, section, str(file)]
    except:
        logger.error("ROW EXTRACTOR FAILED FOR FILE: %s", str(file))
        raise RowExtractorException(filename=file.parts[-1], path=str(file))


def get_rows_from_directory(directory, base_path, glob, row_extractor):
    logger.info("Extracting rows from directory: %s", directory)
    rows = []
    errors = []
    i = 0
    logger.debug("DIRECTORY GLOB: %s", glob)
    for file in directory.glob(glob):
        file = file.relative_to(base_path)
        try:
            row = row_extractor(file)
            rows.append(row)
        except RowExtractorException as e:
            errors.append((e.filename, e.path))
        i += 1
        if i % 500 == 0:
            logger.info("%s files processed", i)
    return (rows, errors)


def export_rows_to_csv(filename, rows):
    logger.info("Starting CSV export for rows")
    count = 0
    with open(filename, 'w', newline='\n') as csvfile:
        writer = csv.writer(csvfile)
        for row in rows:
            writer.writerow(row)
            count += 1
    logger.info("CSV export finished. %s rows exported", count)


def export_errors_to_csv(filename, rows):
    logger.info("Starting CSV export for rows")
    count = 0
    i = filename.index('.csv')
    error_filename = filename[:i] + '-errors' + filename[i:]
    with open(error_filename, 'w', newline='\n') as csvfile:
        writer = csv.writer(csvfile)
        for row in rows:
            writer.writerow(row)
            count += 1
    logger.info("CSV export finished. %s rows exported", count)


def generate_csv_for_type(base_path, glob_prefix, row_extractor, csvfile_path):

    logger.debug("Generating CSV %s with glob prefix %s", csvfile_path, glob_prefix)
    p = Path(base_path)
    dir_results = []
    error_results = []
    for subdir in p.iterdir():
        rows, errors = get_rows_from_directory(
            subdir, base_path, GLOB.format(glob_prefix), row_extractor)
        dir_results.append(rows)
        if errors:
            error_results.append(errors)

    logger.info("All subdirectories have been processed")
    export_rows_to_csv(
        csvfile_path, itertools.chain.from_iterable(dir_results))

    if error_results:
        export_errors_to_csv(
            csvfile_path, itertools.chain.from_iterable(error_results))


def get_csv_generator_for_type(base_path, num, extractor, filename):
    def _something():
        return generate_csv_for_type(base_path, num, extractor, filename)
    return _something


def validate_type_of_cedula(ctx, param, value):
    if not value:
        raise click.BadParameter('El tipo de cedula es obligatorio.')
    return value


COMMAND_CHOICES = ['chacras', 'quintas','manzanas',
                   'fracciones', 'chacras-amanzanadas',
                   'quintas-amanzanadas', 'fraccion-chacra',
                   'fraccion-quinta', 'rural']


@click.command()
@click.option(
    '-t', '--tipo', callback=validate_type_of_cedula,
    type=click.Choice(COMMAND_CHOICES))
def generate_cedulas(tipo):
    def generate_operations(operations):
        op = {}

        for name, num, extractor in operations:
            op[name] = get_csv_generator_for_type(
                BASE_PATH, num[:], extractor, '{}.csv'.format(name))

        return op

    operations = generate_operations([
        ('chacras', '1', simple_row_extractor),
        ('quintas', '2', simple_row_extractor),
        ('manzanas','3', get_lettered_row_extractor('L')),
        ('fracciones', '4', simple_row_extractor),
        ('chacras-amanzanadas','5', get_lettered_row_extractor('L')),
        ('quintas-amanzanadas','6', get_lettered_row_extractor('L')),
        ('fraccion-chacra','7', get_lettered_row_extractor('F')),
        ('fraccion-quinta','8', get_lettered_row_extractor('F')),
        ('rural', '9', simple_row_extractor),
    ])

    logger.info("Starting operation '%s'", tipo)
    operations[tipo]()


if __name__ == '__main__':
    # event_emitter = EventEmitter()
    # event_emitter.on('file-rows-extracted', _on_file_rows_extracted)
    # event_emitter.on('starting-row-processing', lambda: print("Start row processing"))
    # generate_csv_for_chacras(BASE_PATH, '1', event_emitter)
    generate_cedulas()
