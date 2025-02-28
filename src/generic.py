from datetime import datetime, timezone
import time

class Logger:
    def __init__(self, log_file='app.log'):
        self.log_file = log_file

    def log(self, message):
        with open(self.log_file, 'a') as file:
            file.write(f"{datetime.now()}: {message}\n")

class DateTimeOperations:
    def __init__(self):
        self.logger = Logger()

    def utc_to_local(self, utc_dt):
        self.logger.log(f"Converting UTC to local: {utc_dt}")
        return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

    def local_to_utc(self, local_dt):
        self.logger.log(f"Converting local to UTC: {local_dt}")
        return local_dt.astimezone(timezone.utc)

    def from_iso_format(self, iso_str):
        self.logger.log(f"Parsing ISO format date: {iso_str}")
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))

    def format_date(self=None, mod_date=None, local_date=None):
        if self is None:
            self = DateTimeOperations()
        if mod_date is not None:
            out = str(datetime.strptime(str(mod_date), '%Y-%m-%dT%H:%M:%S.%fZ'))
            self.logger.log(f"Formatting mod_date: {mod_date}, Output: {out}")
            return str(self.utc_to_local(self.from_iso_format(mod_date)))
        elif local_date is not None:
            tdate = datetime.fromtimestamp(local_date)
            out = tdate.strftime('%Y-%m-%d %H:%M:%S.') + f"{tdate.microsecond // 1000:03}"
            self.logger.log(f"Formatting local_date: {local_date}, Output: {out}")
            return str(self.parse_custom_format(local_date))
        else:
            self.logger.log("Date missing")
            return None

    def difference_between_dates(self, dt1, dt2):
        self.logger.log(f"Calculating difference between dates: {dt1} and {dt2}")
        return abs(dt1 - dt2)

    def parse_custom_format(self, date_str):  
        try:
            self.logger.log(f"Parsing custom format date: {date_str}")
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
        except TypeError:
            self.logger.log(f"Failed to parse custom format, assuming timestamp: {date_str}")
            return datetime.fromtimestamp(float(date_str))

class FileOperations:
    def __init__(self):
        self.logger = Logger()

if __name__ == '__main__':
    inp = "2025-02-26T12:43:32.569Z"
    test = DateTimeOperations()
    print(test.utc_to_local(test.from_iso_format(inp)))
    dt1 = datetime(2025, 2, 26, 12, 43, 32, 569000, tzinfo=timezone.utc)
    dt2 = datetime(2025, 2, 25, 12, 43, 32, 569000, tzinfo=timezone.utc)
    print(test.difference_between_dates(dt1, dt2))

    custom_date_str = "2025-02-26 18:13:53.328"
    print(test.parse_custom_format(custom_date_str))
