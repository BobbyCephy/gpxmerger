import argparse
import sys
import logging
import logging.config
import gpxpy
import gpxpy.parser as parser
from os import path

nsmap = {}
ext = ".gpx"

# https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
logging.basicConfig(level=logging.DEBUG)
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": "gpxmerger.log",
                "formatter": "standard",
            },
        },
        "loggers": {
            "__main__": {  # name my module
                "level": "DEBUG",
                "propagate": True,
                "handlers": ["file"],
            }
        },
    }
)


def is_gpx(filename):
    logger = logging.getLogger(__name__)
    logger.debug("Checking {f}".format(f=filename))
    return path.splitext(filename)[1] == ext


def load_gpxs(track_files):
    logger = logging.getLogger(__name__)
    gpxs = []

    for track_file in track_files:
        with open(track_file, "r") as gpx_file:
            gpx_parser = parser.GPXParser(gpx_file)
            gpx_parser.parse()
            gpx = gpx_parser.gpx
            gpxs.append(gpx)
            nsmap.update(gpx.nsmap)

    logger.debug("Loaded a total of {s} files".format(s=len(gpxs)))
    return gpxs


def load_tracks(track_files):
    logger = logging.getLogger(__name__)
    gpxs = load_gpxs(track_files)
    tracks = sum((gpx.tracks for gpx in gpxs), [])
    logger.debug("Loaded a total of {s} tracks".format(s=len(tracks)))
    return tracks


def load_segments(track_files):
    logger = logging.getLogger(__name__)
    tracks = load_tracks(track_files)
    segments = sum((track.segments for track in tracks), [])
    logger.debug("Loaded a total of {s} segments".format(s=len(segments)))
    return segments


def load_points(track_files):
    logger = logging.getLogger(__name__)
    segments = load_segments(track_files)
    points = sum((segment.points for segment in segments), [])
    points = list(filter(lambda x: x.time is not None, points))
    points = sorted(points, key=lambda p: p.time)
    logger.debug("Loaded a total of {s} points".format(s=len(points)))
    return points


def get_gpx(data, name=""):
    logger = logging.getLogger(__name__)
    gpx = gpxpy.gpx.GPX()
    gpx.nsmap.update(nsmap)

    if isinstance(data[0], gpxpy.gpx.GPXTrack):
        logger.debug("Generating GPX with {s} tracks".format(s=len(data)))
        gpx.tracks.extend(data)

    else:
        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack(name)
        gpx.tracks.append(gpx_track)

        if isinstance(data[0], gpxpy.gpx.GPXTrackSegment):
            logger.debug(
                "Generating GPX with {s} segments".format(s=len(data))
            )
            gpx_track.segments.extend(data)

        elif isinstance(data[0], gpxpy.gpx.GPXTrackPoint):
            # Create first segment in our GPX track:
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)

            logger.debug("Generating GPX with {s} points".format(s=len(data)))

            # Add points:
            gpx_segment.points.extend(data)

    return gpx


def save(gpx, target_file):
    with open(target_file, "w") as fp:
        logger = logging.getLogger(__name__)
        logger.debug("Saving {f}".format(f=target_file))
        fp.write(gpx.to_xml())
        logger.debug("Done saving")


def get_target(files, target=None):
    logger = logging.getLogger(__name__)

    if not target or not path.isfile(target):
        filename = "merged"
        dirname = path.dirname(files[0])

        if target and path.isdir(target):
            dirname = target

        elif target:
            filename = target

        target = path.join(dirname, filename)

    if not target.endswith(ext):
        target += ext

    logger.debug("Write result to: {f}".format(f=target))
    return target


def get_name(target):
    return path.splitext(path.basename(target))[0]


def merge(files, target=None, segment=False, track=False):
    logger = logging.getLogger(__name__)
    logger.info("Start new merge process")
    track_files = filter(is_gpx, files)

    if segment:
        data = load_segments(track_files)

    elif track:
        data = load_tracks(track_files)

    else:
        data = load_points(track_files)

    target_file = get_target(files, target)
    name = get_name(target_file)
    gpx = get_gpx(data, name)
    save(gpx, target_file)
    logger.info("Finish")


def main():
    parser = argparse.ArgumentParser(
        description="A simple script to merge multiple GPX files into one large GPX file."
    )
    parser.add_argument("input_files", nargs="*", help="input files to merge")
    parser.add_argument("-o", help="output file name, path or directory")
    parser.add_argument(
        "-s", default=False, action="store_true", help=("merge segments")
    )
    parser.add_argument(
        "-t", default=False, action="store_true", help=("merge tracks")
    )

    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    merge(args.input_files, args.o, args.s, args.t)


if __name__ == "__main__":
    main()
