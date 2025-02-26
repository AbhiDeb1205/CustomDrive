from datetime import datetime, timezone
import time

class DateTimeOperations:
    def utc_to_local(self, utc_dt):
        return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

    def local_to_utc(self, local_dt):
        return local_dt.astimezone(timezone.utc)

    def from_iso_format(self, iso_str):
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))

    def format_date(self=None, mod_date=None, local_date=None):
        if self is None:
            self = DateTimeOperations()
        if mod_date is not None:
            out = str(datetime.strptime(str(mod_date), '%Y-%m-%dT%H:%M:%S.%fZ'))
            print("+++++++")
            print(f"{mod_date=}")
            print(f"{out=}")
            print("+++++++")
            # return str(datetime.strptime(str(mod_date), '%Y-%m-%dT%H:%M:%S.%fZ'))
            return str(self.utc_to_local(self.from_iso_format(mod_date)))
        elif local_date is not None:
            tdate = datetime.fromtimestamp(local_date)
            out = tdate.strftime('%Y-%m-%d %H:%M:%S.') + f"{tdate.microsecond // 1000:03}"
            print("+++++++")
            print(f"{local_date=}")
            print(f"{out=}")
            print("+++++++")
            # return tdate.strftime('%Y-%m-%d %H:%M:%S.') + f"{tdate.microsecond // 1000:03}"
            return str(self.parse_custom_format(local_date))
        else:
            print("Date missing")
            return None

    def difference_between_dates(self, dt1, dt2):
        return abs(dt1 - dt2)

    def parse_custom_format(self, date_str):  
        try:
            # Try to parse as a custom date format
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
        except TypeError:
            # If parsing fails, assume it's a timestamp from os.path.getmtime
            return datetime.fromtimestamp(float(date_str))

if __name__ == '__main__':
    inp = "2025-02-26T12:43:32.569Z"
    test = DateTimeOperations()
    print(test.utc_to_local(test.from_iso_format(inp)))
    dt1 = datetime(2025, 2, 26, 12, 43, 32, 569000, tzinfo=timezone.utc)
    dt2 = datetime(2025, 2, 25, 12, 43, 32, 569000, tzinfo=timezone.utc)
    print(test.difference_between_dates(dt1, dt2))

    custom_date_str = "2025-02-26 18:13:53.328"
    print(test.parse_custom_format(custom_date_str))
