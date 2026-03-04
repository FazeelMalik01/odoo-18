# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, time, timedelta
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def _get_contract(self, employee, date_from, date_to):
        """
        Override to ensure computed contracts don't use standard wage calculation
        """
        contract = super(HrPayslip, self)._get_contract(employee, date_from, date_to)
        
        # For computed contracts, we'll handle wage calculation in compute_sheet
        # This method is called before compute_sheet, so we just return the contract
        return contract

    def _is_public_holiday(self, date_to_check, contract=None):
        """
        Check if a given date is a public holiday.
        Returns True if the date is a public holiday, False otherwise.
        
        Args:
            date_to_check: The date to check (date object)
            contract: The hr.contract object to check work schedule (optional)
        """
        try:
            # Convert date to date object if it's datetime
            if isinstance(date_to_check, datetime):
                check_date = date_to_check.date()
            elif isinstance(date_to_check, str):
                check_date = fields.Date.from_string(date_to_check)
            else:
                check_date = date_to_check
            
            _logger.error(f"  Checking for public holiday on date: {check_date}")
            
            # Convert check_date to datetime for comparison
            # IMPORTANT: Odoo stores datetimes in UTC, so we need to convert the local date to UTC datetime range
            # Use Odoo's Datetime helper to handle timezone conversion
            # Create datetime range for the check date (start and end of day)
            check_datetime_start_local = datetime.combine(check_date, time(0, 0, 0))
            check_datetime_stop_local = datetime.combine(check_date, time(23, 59, 59))
            
            # Convert local datetime to UTC using Odoo's context_timestamp in reverse
            # We need to convert from user's local timezone to UTC
            # Odoo stores datetimes as naive UTC, so we create naive UTC datetimes
            # by using the user's timezone to convert
            from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
            import pytz
            
            user_tz = self.env.user.tz or 'UTC'
            local_tz = pytz.timezone(user_tz)
            utc_tz = pytz.UTC
            
            # Localize the local datetime and convert to UTC
            local_start_aware = local_tz.localize(check_datetime_start_local)
            local_end_aware = local_tz.localize(check_datetime_stop_local)
            
            check_datetime_start_utc = local_start_aware.astimezone(utc_tz).replace(tzinfo=None)
            check_datetime_stop_utc = local_end_aware.astimezone(utc_tz).replace(tzinfo=None)
            
            _logger.error(f"  Local date range: {check_datetime_start_local} to {check_datetime_stop_local} (timezone: {user_tz})")
            _logger.error(f"  UTC date range for search: {check_datetime_start_utc} to {check_datetime_stop_utc}")
            
            # In Odoo 18, public holidays are stored in resource.calendar.leaves model
            # This model uses date_from and date_to fields (not date_start/date_stop)
            try:
                # Use self.env['model_name'] instead of self.env.get() for models
                public_holiday_model = self.env['resource.calendar.leaves'].sudo()
                _logger.error(f"  Trying model: resource.calendar.leaves")
                
                # First, try to get all holidays to see what's available (for debugging)
                all_holidays = public_holiday_model.search([], limit=10)
                _logger.error(f"  Found {len(all_holidays)} total public holidays in resource.calendar.leaves")
                for h in all_holidays:
                    h_name = h.name if hasattr(h, 'name') else 'Unknown'
                    h_from = h.date_from if hasattr(h, 'date_from') else 'N/A'
                    h_to = h.date_to if hasattr(h, 'date_to') else 'N/A'
                    _logger.error(f"    Holiday: {h_name}, From: {h_from}, To: {h_to}")
                
                # resource.calendar.leaves uses date_from and date_to fields
                # Search for holidays that overlap with the check date (using UTC datetimes)
                # Also filter by work schedule (calendar_id) if contract is provided
                domain = [
                    ('date_from', '<=', check_datetime_stop_utc),
                    ('date_to', '>=', check_datetime_start_utc),
                ]
                
                # If contract is provided, filter by the contract's work schedule
                if contract and contract.resource_calendar_id:
                    domain.append(('calendar_id', '=', contract.resource_calendar_id.id))
                    _logger.error(f"  Filtering holidays by work schedule: {contract.resource_calendar_id.name} (ID: {contract.resource_calendar_id.id})")
                else:
                    _logger.error(f"  No contract or work schedule provided - checking all holidays")
                
                holidays = public_holiday_model.search(domain, limit=5)
                
                if holidays:
                    for holiday in holidays:
                        holiday_name = holiday.name if hasattr(holiday, 'name') else 'Unknown'
                        holiday_calendar = holiday.calendar_id.name if hasattr(holiday, 'calendar_id') and holiday.calendar_id else 'No Schedule'
                        _logger.error(f"  Found matching holiday: {holiday_name}, From: {holiday.date_from}, To: {holiday.date_to}, Schedule: {holiday_calendar}")
                    
                    holiday_name = holidays[0].name if hasattr(holidays[0], 'name') else 'Unknown'
                    _logger.error(f"  ✓ Public holiday detected: {holiday_name} (from resource.calendar.leaves)")
                    return True
                else:
                    _logger.error(f"  No holidays found in resource.calendar.leaves for date range {check_datetime_start_utc} to {check_datetime_stop_utc}")
            except Exception as e:
                _logger.error(f"  Error checking resource.calendar.leaves: {str(e)}")
                import traceback
                _logger.error(traceback.format_exc())
            
            _logger.error(f"  ✗ No public holiday found for date: {check_date}")
        except Exception as e:
            _logger.warning(f"Could not check for public holiday: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
        
        return False

    def _get_standard_hours_per_day(self, contract):
        """
        Get standard working hours per day from the contract's resource calendar.
        Returns 8.0 for normal schedules, 2.0 for evening schedules, or 8.0 as default.
        """
        if not contract.resource_calendar_id:
            return 8.0  # Default to 8 hours if no calendar
        
        calendar = contract.resource_calendar_id
        
        # Check if it's an evening schedule by looking at the calendar name
        if hasattr(calendar, 'name') and calendar.name:
            calendar_name_lower = calendar.name.lower()
            if 'evening' in calendar_name_lower:
                return 2.0
        
        # Check hours per week - if less than 10 hours/week, likely evening schedule
        if hasattr(calendar, 'hours_per_week') and calendar.hours_per_week:
            if calendar.hours_per_week <= 10:
                return 2.0
        
        # Default to 8 hours for normal schedule
        return 8.0

    def _calculate_overtime(self, total_hours, standard_hours, is_sunday, matching_rule):
        """
        Calculate overtime hours and amount.
        
        Args:
            total_hours: Total hours worked in the day
            standard_hours: Standard working hours per day (8 for normal, 2 for evening)
            is_sunday: Boolean indicating if it's Sunday
            matching_rule: The matching salary calculation rule
        
        Returns:
            tuple: (regular_hours, overtime_hours, regular_amount, overtime_amount)
        """
        regular_hours = min(total_hours, standard_hours)
        overtime_hours = max(0.0, total_hours - standard_hours)
        
        # Get regular rate
        if matching_rule.hourly_pay_rate > 0:
            regular_rate = matching_rule.hourly_pay_rate
        else:
            regular_rate = matching_rule.weekly_pay_rate / 38.0 if matching_rule.weekly_pay_rate > 0 else 0.0
        
        regular_amount = regular_hours * regular_rate
        overtime_amount = 0.0
        
        if overtime_hours > 0:
            if is_sunday:
                # Sunday overtime: use overtime_sunday rate for all overtime hours
                overtime_amount = overtime_hours * matching_rule.overtime_sunday
                _logger.error(f"    Sunday Overtime: {overtime_hours:.2f} hours × {matching_rule.overtime_sunday:.2f} = {overtime_amount:.2f}")
            else:
                # Weekday overtime: first 2 hours use overtime_first_2_hours, rest use overtime_after_2_hours
                first_2_overtime_hours = min(overtime_hours, 2.0)
                after_2_overtime_hours = max(0.0, overtime_hours - 2.0)
                
                first_2_amount = first_2_overtime_hours * matching_rule.overtime_first_2_hours
                after_2_amount = after_2_overtime_hours * matching_rule.overtime_after_2_hours
                
                overtime_amount = first_2_amount + after_2_amount
                
                _logger.error(f"    Overtime breakdown:")
                _logger.error(f"      First 2 hours: {first_2_overtime_hours:.2f} × {matching_rule.overtime_first_2_hours:.2f} = {first_2_amount:.2f}")
                if after_2_overtime_hours > 0:
                    _logger.error(f"      After 2 hours: {after_2_overtime_hours:.2f} × {matching_rule.overtime_after_2_hours:.2f} = {after_2_amount:.2f}")
        
        return regular_hours, overtime_hours, regular_amount, overtime_amount

    def _get_matching_rule(self, contract):
        """
        Get the matching salary calculation rule based on age, level, and employment type
        """
        if not contract.salary_computation_rule_id:
            return False
        
        rule = contract.salary_computation_rule_id
        age = contract.age
        level = contract.level
        employment_type = contract.employment_type
        
        if not age or not level or not employment_type:
            return False
        
        # Determine which age classification to use
        age_classification_model = False
        age_classification_field = False
        
        if age < 16:
            age_classification_model = 'custom__payroll.salary_calculation_rule.under_16'
            age_classification_field = 'under_16_ids'
        elif age == 16:
            age_classification_model = 'custom__payroll.salary_calculation_rule.age_16'
            age_classification_field = 'age_16_ids'
        elif age == 17:
            age_classification_model = 'custom__payroll.salary_calculation_rule.age_17'
            age_classification_field = 'age_17_ids'
        elif age == 18:
            age_classification_model = 'custom__payroll.salary_calculation_rule.age_18'
            age_classification_field = 'age_18_ids'
        elif age == 19:
            age_classification_model = 'custom__payroll.salary_calculation_rule.age_19'
            age_classification_field = 'age_19_ids'
        elif age == 20:
            age_classification_model = 'custom__payroll.salary_calculation_rule.age_20'
            age_classification_field = 'age_20_ids'
        else:  # age > 20
            age_classification_model = 'custom__payroll.salary_calculation_rule.adults'
            age_classification_field = 'adults_ids'
        
        # Get the age classification records for this rule
        age_classifications = getattr(rule, age_classification_field)
        
        # Find matching record based on level and employment_type
        matching_rule = age_classifications.filtered(
            lambda r: r.classification == level and r.employment_type == employment_type
        )
        
        if not matching_rule:
            raise UserError(
                f"No matching salary rule found for Age: {age}, Level: {level}, Type: {employment_type}. "
                f"Please configure the salary calculation rule."
            )
        
        # Return the first matching rule (should be only one)
        return matching_rule[0]

    def _get_rate_for_work_type(self, contract, work_type='normal'):
        """
        Get the appropriate rate based on work type
        work_type can be: 'normal', 'evening', 'evening_midnight', 'saturday', 'sunday'
        """
        matching_rule = self._get_matching_rule(contract)
        if not matching_rule:
            return 0.0
        
        if work_type == 'evening':
            return matching_rule.evening_work_rate
        elif work_type == 'evening_midnight':
            return matching_rule.evening_work_rate_midnight
        elif work_type == 'saturday':
            return matching_rule.saturday_rate
        elif work_type == 'sunday':
            return matching_rule.sunday_rate
        else:  # normal
            if contract.pay_rate == 'hourly':
                return matching_rule.hourly_pay_rate
            else:
                return matching_rule.weekly_pay_rate

    def _calculate_hours_by_time_period(self, date_start, date_stop):
        """
        Calculate hours worked in different time periods:
        - Normal hours (6am to 10pm)
        - Evening hours (10pm to 11:59pm)
        - Evening midnight hours (12am to 6am)
        Returns: (normal_hours, evening_hours, evening_midnight_hours, is_saturday, is_sunday)
        """
        if not date_start or not date_stop:
            return 0.0, 0.0, 0.0, False, False
        
        # Convert to datetime
        if isinstance(date_start, str):
            date_start = fields.Datetime.from_string(date_start)
        elif not isinstance(date_start, datetime):
            date_start = fields.Datetime.to_datetime(date_start)
            
        if isinstance(date_stop, str):
            date_stop = fields.Datetime.from_string(date_stop)
        elif not isinstance(date_stop, datetime):
            date_stop = fields.Datetime.to_datetime(date_stop)
        
        # Handle timezone-aware datetimes - convert to naive by extracting local time
        # This preserves the local time values while making comparisons work
        if date_start.tzinfo is not None:
            # Extract naive datetime from timezone-aware datetime (keeps local time)
            date_start = date_start.replace(tzinfo=None)
        if date_stop.tzinfo is not None:
            date_stop = date_stop.replace(tzinfo=None)
        
        # Get the day of week from the start date (0 = Monday, 6 = Sunday)
        day_of_week = date_start.weekday()
        is_saturday = day_of_week == 5
        is_sunday = day_of_week == 6
        
        normal_hours = 0.0
        evening_hours = 0.0
        evening_midnight_hours = 0.0
        
        # Time boundaries (as per user requirements):
        # - Normal hours: 6:00 AM to 9:59 PM (actually 6:00 AM to 10:00 PM, but we use < 22:00)
        # - Evening hours: 10:00 PM to 11:59 PM (22:00 to 23:59)
        # - Midnight hours: 12:00 AM to 5:59 AM (00:00 to 05:59)
        normal_start = time(6, 0)      # 6:00 AM
        normal_end = time(22, 0)        # 10:00 PM (9:59 PM = 21:59, but we use < 22:00)
        evening_start = time(22, 0)     # 10:00 PM
        evening_end = time(23, 59, 59)  # 11:59 PM
        midnight_start = time(0, 0)    # 12:00 AM (midnight)
        midnight_end = time(5, 59, 59)  # 5:59 AM
        
        # Process work entry by breaking it into time segments
        # Handle work entries that span multiple days
        current = date_start
        end = date_stop
        
        # Debug logging
        _logger.error(f"  Time calculation - Start: {date_start}, End: {date_stop}")
        
        while current < end:
            current_time = current.time()
            current_date = current.date()
            
            # Determine which period we're in based on current time
            # Priority order: Midnight (00:00-05:59) -> Normal (06:00-21:59) -> Evening (22:00-23:59)
            
            # Check if we're in midnight period (12:00 AM to 5:59 AM)
            # Midnight period: 00:00:00 to 05:59:59
            if current_time >= midnight_start and current_time < normal_start:
                # Midnight period (12:00 AM to 5:59 AM)
                # Calculate until 6am or work entry end, whichever comes first
                period_end = min(end, datetime.combine(current_date, normal_start))
                hours = (period_end - current).total_seconds() / 3600.0
                if hours > 0:
                    evening_midnight_hours += hours
                    _logger.error(f"    Midnight period (12am-5:59am): {current} to {period_end} = {hours:.2f} hours")
                current = period_end
                if current >= end:
                    break
                # Continue to next period if we haven't reached the end
                continue
                    
            # Check if we're in normal period (6:00 AM to 9:59 PM, actually < 22:00)
            elif current_time >= normal_start and current_time < evening_start:
                # Normal period (6:00 AM to 9:59 PM / < 10:00 PM)
                period_end = min(end, datetime.combine(current_date, evening_start))
                hours = (period_end - current).total_seconds() / 3600.0
                if hours > 0:
                    normal_hours += hours
                    _logger.error(f"    Normal period (6am-9:59pm): {current} to {period_end} = {hours:.2f} hours")
                current = period_end
                if current >= end:
                    break
                # Continue to next period if we haven't reached the end
                continue
                    
            # Check if we're in evening period (10:00 PM to 11:59 PM)
            elif current_time >= evening_start:
                # Evening period (10:00 PM to 11:59 PM)
                # Calculate until end of day (midnight) or work entry end
                next_day = current_date + timedelta(days=1)
                midnight_next = datetime.combine(next_day, midnight_start)
                period_end = min(end, midnight_next)
                hours = (period_end - current).total_seconds() / 3600.0
                if hours > 0:
                    evening_hours += hours
                    _logger.error(f"    Evening period (10pm-11:59pm): {current} to {period_end} = {hours:.2f} hours")
                current = period_end
                if current >= end:
                    break
                # If we've reached midnight and there's more time, continue to midnight period
                if current < end:
                    # Move to next day's midnight period
                    current = datetime.combine(next_day, midnight_start)
                    continue
            else:
                # Should not reach here, but break to avoid infinite loop
                _logger.error(f"    Unexpected time period: {current_time}, breaking loop")
                break
        
        _logger.error(f"  Final hours - Normal: {normal_hours:.2f}, Evening: {evening_hours:.2f}, Midnight: {evening_midnight_hours:.2f}")
        return normal_hours, evening_hours, evening_midnight_hours, is_saturday, is_sunday

    def _calculate_salary_from_work_entries(self, contract, matching_rule, date_from, date_to):
        """
        Calculate salary based on work entries with time and day-based rates
        """
        # Get work entries for the payslip period
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('date_start', '>=', date_from),
            ('date_stop', '<=', date_to),
            ('state', '=', 'validated')
        ])
        
        total_salary = 0.0
        normal_hours_total = 0.0
        evening_hours_total = 0.0
        evening_midnight_hours_total = 0.0
        saturday_hours_total = 0.0
        sunday_hours_total = 0.0
        
        for work_entry in work_entries:
            normal_hours, evening_hours, evening_midnight_hours, is_saturday, is_sunday = \
                self._calculate_hours_by_time_period(work_entry.date_start, work_entry.date_stop)
            
            # Determine which rate to use based on day
            if is_sunday:
                # Sunday rate applies to all hours
                rate = matching_rule.sunday_rate
                sunday_hours_total += (normal_hours + evening_hours + evening_midnight_hours)
                total_salary += (normal_hours + evening_hours + evening_midnight_hours) * rate
            elif is_saturday:
                # Saturday rate applies to all hours
                rate = matching_rule.saturday_rate
                saturday_hours_total += (normal_hours + evening_hours + evening_midnight_hours)
                total_salary += (normal_hours + evening_hours + evening_midnight_hours) * rate
            else:
                # Weekday - apply different rates for different time periods
                # Normal hours (6am to 10pm)
                # Always use hourly_pay_rate from the rule (preferred)
                # If hourly_pay_rate is 0, fallback to weekly_pay_rate / 38
                if matching_rule.hourly_pay_rate > 0:
                    normal_rate = matching_rule.hourly_pay_rate
                else:
                    # Fallback to weekly rate if hourly is not set
                    normal_rate = matching_rule.weekly_pay_rate / 38.0 if matching_rule.weekly_pay_rate > 0 else 0.0
                
                normal_hours_total += normal_hours
                total_salary += normal_hours * normal_rate
                
                # Evening hours (10pm to 11:59pm)
                evening_hours_total += evening_hours
                total_salary += evening_hours * matching_rule.evening_work_rate
                
                # Evening midnight hours (12am to 6am)
                evening_midnight_hours_total += evening_midnight_hours
                total_salary += evening_midnight_hours * matching_rule.evening_work_rate_midnight
        
        return {
            'total_salary': total_salary,
            'normal_hours': normal_hours_total,
            'evening_hours': evening_hours_total,
            'evening_midnight_hours': evening_midnight_hours_total,
            'saturday_hours': saturday_hours_total,
            'sunday_hours': sunday_hours_total
        }

    def compute_sheet(self):
        """
        Override compute_sheet to use custom salary calculation rules
        For contracts with salary_computation_type = 'computed', we completely override
        the standard computation to use our custom rules based on age, level, type, and work entries
        """
        # Force logging to console and file
        print("=" * 80)
        print("CUSTOM PAYSLIP COMPUTATION METHOD CALLED!")
        print("=" * 80)
        _logger.error("=" * 80)  # Use ERROR level to ensure it shows
        _logger.error("CUSTOM PAYSLIP COMPUTATION METHOD CALLED!")
        _logger.error("=" * 80)
        
        try:
            _logger.error(f"=== CUSTOM PAYSLIP COMPUTATION STARTED ===")
            _logger.error(f"Processing {len(self)} payslip(s)")
            print(f"Processing {len(self)} payslip(s)")
            
            # Separate payslips that need custom computation from standard ones
            custom_payslips = self.filtered(lambda p: p.contract_id and p.contract_id.salary_computation_type == 'computed')
            standard_payslips = self - custom_payslips
            
            _logger.error(f"Custom payslips: {len(custom_payslips)}, Standard payslips: {len(standard_payslips)}")
            print(f"Custom payslips: {len(custom_payslips)}, Standard payslips: {len(standard_payslips)}")
            
            # Debug: Log all payslips and their contract computation types
            for p in self:
                if p.contract_id:
                    info_msg = (f"Payslip {p.id}: Contract={p.contract_id.name}, "
                               f"Computation Type={p.contract_id.salary_computation_type}, "
                               f"Rule ID={p.contract_id.salary_computation_rule_id.id if p.contract_id.salary_computation_rule_id else 'None'}")
                    _logger.error(info_msg)
                    print(info_msg)
                else:
                    _logger.error(f"Payslip {p.id} has no contract!")
                    print(f"Payslip {p.id} has no contract!")
        except Exception as e:
            error_msg = f"Error in compute_sheet filtering: {str(e)}"
            _logger.error(error_msg, exc_info=True)
            print(error_msg)
            import traceback
            traceback.print_exc()
            raise
        
        # IMPORTANT: Process standard payslips FIRST, then custom ones
        # This ensures standard payslips are computed even if custom processing fails
        standard_result = True
        if standard_payslips:
            try:
                _logger.error(f"Processing {len(standard_payslips)} standard payslip(s) FIRST with super().compute_sheet()")
                print(f"Processing {len(standard_payslips)} standard payslip(s) FIRST with super().compute_sheet()")
                standard_result = super(HrPayslip, standard_payslips).compute_sheet()
            except Exception as e:
                error_msg = f"ERROR processing standard payslips: {str(e)}"
                _logger.error(error_msg, exc_info=True)
                print(error_msg)
                import traceback
                traceback.print_exc()
                # If standard processing fails, we still try custom processing
                # But we'll re-raise if there are no custom payslips
                if not custom_payslips:
                    raise
                standard_result = True
        
        # Process custom computation payslips (these will override standard if they exist)
        for payslip in custom_payslips:
            try:
                _logger.info(f"Processing custom payslip ID: {payslip.id}")
                
                contract = payslip.contract_id
                if not contract:
                    _logger.error(f"Payslip {payslip.id} has no contract!")
                    standard_payslips |= payslip
                    continue
                
                _logger.info(f"Contract: {contract.name}, "
                            f"Computation Type: {contract.salary_computation_type}, "
                            f"Age: {contract.age}, "
                            f"Level: {contract.level}, "
                            f"Type: {contract.employment_type}, "
                            f"Rule ID: {contract.salary_computation_rule_id.id if contract.salary_computation_rule_id else 'None'}")
                
                matching_rule = self._get_matching_rule(contract)
                
                if not matching_rule:
                    _logger.warning(f"No matching rule found for payslip {payslip.id}, falling back to standard")
                    # If no matching rule, fall back to standard computation
                    standard_payslips |= payslip
                    continue
                
                _logger.info(f"Matching rule found: Classification={matching_rule.classification}, "
                            f"Employment Type={matching_rule.employment_type}, "
                            f"Hourly Rate={matching_rule.hourly_pay_rate}, "
                            f"Saturday Rate={matching_rule.saturday_rate}, "
                            f"Sunday Rate={matching_rule.sunday_rate}")
                
                # Validate that we have the required rates from the rule
                # IMPORTANT: We ONLY use rates from the salary calculation rule, NEVER from contract.wage or contract.hourly_wage
                if matching_rule.hourly_pay_rate == 0 and matching_rule.weekly_pay_rate == 0:
                    raise UserError(
                        f"Salary calculation rule for Age: {contract.age}, Level: {contract.level}, "
                        f"Type: {contract.employment_type} has no hourly_pay_rate or weekly_pay_rate configured. "
                        f"Please set the hourly_pay_rate field in the salary calculation rule. "
                        f"The system will NOT use the contract's hourly_wage field for computed salaries."
                    )
                
                # Additional validation - ensure hourly_pay_rate is set for proper computation
                if matching_rule.hourly_pay_rate == 0:
                    # If hourly_pay_rate is 0, we can use weekly_pay_rate as fallback, but warn the user
                    if matching_rule.weekly_pay_rate == 0:
                        raise UserError(
                            f"Salary calculation rule for Age: {contract.age}, Level: {contract.level}, "
                            f"Type: {contract.employment_type} has hourly_pay_rate = 0.00. "
                            f"Please set the hourly_pay_rate field in the Adults tab of the salary calculation rule. "
                            f"The system uses hourly_pay_rate from the rule, NOT from contract hourly_wage field."
                        )
                
                # IMPORTANT: Store original contract wage
                # We'll restore it after computation, but we don't set it to 0.0 anymore
                # because the amount field on worked_days might be computed from contract.wage
                original_wage = contract.wage
                original_hourly_wage = getattr(contract, 'hourly_wage', False)
                
                # Get work entries for the payslip period
                # CRITICAL: Handle timezone conversion - work entries are stored in UTC, but payslip dates are local
                # We need to convert work entry datetimes to user timezone before comparing dates
                payslip_date = payslip.date_from
                
                # Search for ALL work entries for this employee first to see what exists
                all_work_entries = self.env['hr.work.entry'].search([
                    ('employee_id', '=', contract.employee_id.id),
                ], order='date_start desc', limit=50)
                
                _logger.error(f"=== DEBUG: All recent work entries for employee {contract.employee_id.name} (ID: {contract.employee_id.id}) ===")
                _logger.error(f"Total work entries found: {len(all_work_entries)}")
                _logger.error(f"Payslip date (local): {payslip_date}")
                
                # Filter work entries by converting UTC datetime to user's local timezone and comparing dates
                work_entries = []
                for we in all_work_entries:
                    # Convert UTC datetime to user's local timezone
                    local_start = Datetime.context_timestamp(self, we.date_start)
                    local_stop = Datetime.context_timestamp(self, we.date_stop)
                    local_start_date = local_start.date()
                    local_stop_date = local_stop.date()
                    
                    # Check if work entry starts on the payslip date (in local timezone)
                    matches_date = local_start_date == payslip_date
                    matches_state = we.state in ['validated', 'draft']
                    
                    _logger.error(f"  Work Entry ID {we.id}:")
                    _logger.error(f"    UTC: {we.date_start} to {we.date_stop}")
                    _logger.error(f"    Local: {local_start} to {local_stop}")
                    _logger.error(f"    Local Date: {local_start_date} (Payslip Date: {payslip_date})")
                    _logger.error(f"    State: {we.state}")
                    _logger.error(f"    Matches Date: {matches_date}, Matches State: {matches_state}")
                    
                    if matches_date and matches_state:
                        work_entries.append(we)
                        _logger.error(f"    ✓ MATCHES - Will be included in payslip calculation")
                    else:
                        _logger.error(f"    ✗ Does NOT match - Date match: {matches_date}, State match: {matches_state}")
                
                _logger.error(f"=== Work entries found for payslip period ===")
                _logger.error(f"Payslip date (local): {payslip_date}")
                _logger.error(f"Found {len(work_entries)} work entries for payslip {payslip.id}")
                for we in work_entries:
                    local_start = Datetime.context_timestamp(self, we.date_start)
                    local_stop = Datetime.context_timestamp(self, we.date_stop)
                    _logger.error(f"  Work Entry ID {we.id}: Local {local_start} to {local_stop}, State: {we.state}")
                
                # Clear existing lines - use sudo to avoid permission issues
                # Check if lines exist before unlinking to avoid errors
                if payslip.worked_days_line_ids:
                    try:
                        payslip.worked_days_line_ids.unlink()
                    except Exception as e:
                        _logger.warning(f"Could not unlink worked_days_line_ids: {str(e)}")
                if payslip.line_ids:
                    try:
                        payslip.line_ids.unlink()
                    except Exception as e:
                        _logger.warning(f"Could not unlink line_ids: {str(e)}")
                
                # Calculate salary based on work entries
                total_salary = 0.0
                total_worked_days = 0.0
                total_hours = 0.0
                
                # Get standard hours per day from contract's work schedule
                standard_hours_per_day = self._get_standard_hours_per_day(contract)
                _logger.error(f"Standard hours per day (from work schedule): {standard_hours_per_day:.2f}")
                
                # Process each work entry
                for work_entry in work_entries:
                    # Convert UTC datetime to local timezone for time calculation
                    # The time periods (6am-10pm, 10pm-11:59pm, 12am-6am) are based on LOCAL time
                    local_start = Datetime.context_timestamp(self, work_entry.date_start)
                    local_stop = Datetime.context_timestamp(self, work_entry.date_stop)
                    
                    # Calculate hours by time period using LOCAL timezone
                    normal_hours, evening_hours, evening_midnight_hours, is_saturday, is_sunday = \
                        self._calculate_hours_by_time_period(local_start, local_stop)
                    
                    entry_total_hours = normal_hours + evening_hours + evening_midnight_hours
                    total_hours += entry_total_hours
                    
                    _logger.error(f"Processing Work Entry {work_entry.id}:")
                    _logger.error(f"  UTC: {work_entry.date_start} to {work_entry.date_stop}")
                    _logger.error(f"  Local: {local_start} to {local_stop}")
                    _logger.error(f"  Total Hours: {entry_total_hours:.2f}")
                    _logger.error(f"  Hours breakdown - Normal (6am-10pm): {normal_hours:.2f}, Evening (10pm-11:59pm): {evening_hours:.2f}, Midnight (12am-6am): {evening_midnight_hours:.2f}")
                    _logger.error(f"  Is Saturday: {is_saturday}, Is Sunday: {is_sunday}")
                    _logger.error(f"  Rates - Hourly: {matching_rule.hourly_pay_rate:.2f}, Evening (10pm-11:59pm): {matching_rule.evening_work_rate:.2f}, Midnight (12am-6am): {matching_rule.evening_work_rate_midnight:.2f}")
                    _logger.error(f"  Rates - Saturday: {matching_rule.saturday_rate:.2f}, Sunday: {matching_rule.sunday_rate:.2f}")
                    _logger.error(f"  Rates - Public Holiday: {matching_rule.public_holiday_rate:.2f}, Overtime Public Holiday: {matching_rule.overtime_public_holiday:.2f}")
                    
                    # Calculate amount based on day type and time periods with overtime
                    # IMPORTANT: Always use the rates from the matching rule
                    
                    # Check if this work entry falls on a public holiday
                    # Pass the contract to filter holidays by work schedule
                    entry_date = local_start.date()
                    is_public_holiday = self._is_public_holiday(entry_date, contract=contract)
                    _logger.error(f"  Is Public Holiday: {is_public_holiday} (checked date: {entry_date}, work schedule: {contract.resource_calendar_id.name if contract and contract.resource_calendar_id else 'None'})")
                    
                    # First, determine regular and overtime hours
                    regular_hours = min(entry_total_hours, standard_hours_per_day)
                    overtime_hours = max(0.0, entry_total_hours - standard_hours_per_day)
                    
                    # Public holiday takes priority over Sunday/Saturday
                    if is_public_holiday:
                        _logger.error(f"  ✓ PUBLIC HOLIDAY DETECTED - Using public holiday rates")
                        # Public holiday: regular hours use public_holiday_rate, overtime uses overtime_public_holiday
                        regular_amount = regular_hours * matching_rule.public_holiday_rate
                        
                        # Calculate overtime amount
                        if overtime_hours > 0:
                            overtime_amount = overtime_hours * matching_rule.overtime_public_holiday
                        else:
                            overtime_amount = 0.0
                        
                        entry_amount = regular_amount + overtime_amount
                        
                        _logger.error(f"  PUBLIC HOLIDAY calculation:")
                        _logger.error(f"    Regular hours: {regular_hours:.2f} × {matching_rule.public_holiday_rate:.2f} = {regular_amount:.2f}")
                        if overtime_hours > 0:
                            _logger.error(f"    Overtime hours: {overtime_hours:.2f} × {matching_rule.overtime_public_holiday:.2f} = {overtime_amount:.2f}")
                        _logger.error(f"    Total: {entry_amount:.2f}")
                    elif is_sunday:
                        # Sunday: regular hours use Sunday rate, overtime uses overtime_sunday rate
                        regular_amount = regular_hours * matching_rule.sunday_rate
                        
                        # Calculate overtime amount
                        if overtime_hours > 0:
                            overtime_amount = overtime_hours * matching_rule.overtime_sunday
                        else:
                            overtime_amount = 0.0
                        
                        entry_amount = regular_amount + overtime_amount
                        
                        _logger.error(f"  SUNDAY calculation:")
                        _logger.error(f"    Regular hours: {regular_hours:.2f} × {matching_rule.sunday_rate:.2f} = {regular_amount:.2f}")
                        if overtime_hours > 0:
                            _logger.error(f"    Overtime hours: {overtime_hours:.2f} × {matching_rule.overtime_sunday:.2f} = {overtime_amount:.2f}")
                        _logger.error(f"    Total: {entry_amount:.2f}")
                    elif is_saturday:
                        # Saturday: regular hours use Saturday rate, overtime uses overtime rates
                        regular_amount = regular_hours * matching_rule.saturday_rate
                        
                        # Calculate overtime amount (first 2 hours, then after 2 hours)
                        if overtime_hours > 0:
                            first_2_overtime_hours = min(overtime_hours, 2.0)
                            after_2_overtime_hours = max(0.0, overtime_hours - 2.0)
                            overtime_amount = (first_2_overtime_hours * matching_rule.overtime_first_2_hours) + \
                                            (after_2_overtime_hours * matching_rule.overtime_after_2_hours)
                        else:
                            overtime_amount = 0.0
                        
                        entry_amount = regular_amount + overtime_amount
                        
                        _logger.error(f"  SATURDAY calculation:")
                        _logger.error(f"    Regular hours: {regular_hours:.2f} × {matching_rule.saturday_rate:.2f} = {regular_amount:.2f}")
                        if overtime_hours > 0:
                            _logger.error(f"    Overtime: {overtime_amount:.2f} (First 2: {min(overtime_hours, 2.0):.2f} × {matching_rule.overtime_first_2_hours:.2f}, After 2: {max(0.0, overtime_hours - 2.0):.2f} × {matching_rule.overtime_after_2_hours:.2f})")
                        _logger.error(f"    Total: {entry_amount:.2f}")
                    else:
                        # Weekday (Monday to Friday): Calculate regular hours and overtime
                        # Regular hours use time-based rates, overtime uses overtime rates
                        
                        # Get regular rate based on time period
                        if matching_rule.hourly_pay_rate > 0:
                            normal_rate = matching_rule.hourly_pay_rate
                        else:
                            normal_rate = matching_rule.weekly_pay_rate / 38.0 if matching_rule.weekly_pay_rate > 0 else 0.0
                            if normal_rate == 0:
                                raise UserError(
                                    f"Salary calculation rule for Age: {contract.age}, Level: {contract.level}, "
                                    f"Type: {contract.employment_type} has no hourly_pay_rate or weekly_pay_rate set. "
                                    f"Please configure the hourly_pay_rate field in the salary calculation rule."
                                )
                        
                        # Calculate regular hours amount based on time periods
                        # Regular hours are up to standard_hours_per_day, rest is overtime
                        # For regular hours, apply time-based rates
                        # For overtime hours, apply overtime rates
                        
                        # First, calculate regular amount using time-based rates
                        if evening_midnight_hours > 0 and normal_hours == 0 and evening_hours == 0:
                            # Work entry is ENTIRELY in midnight period (12am-6am)
                            # Regular hours use midnight rate, overtime uses overtime rates
                            regular_midnight_hours = min(regular_hours, evening_midnight_hours)
                            
                            regular_amount = regular_midnight_hours * matching_rule.evening_work_rate_midnight
                            
                            # Calculate overtime amount (first 2 hours, then after 2 hours)
                            if overtime_hours > 0:
                                first_2_overtime_hours = min(overtime_hours, 2.0)
                                after_2_overtime_hours = max(0.0, overtime_hours - 2.0)
                                overtime_amount = (first_2_overtime_hours * matching_rule.overtime_first_2_hours) + \
                                                (after_2_overtime_hours * matching_rule.overtime_after_2_hours)
                            else:
                                overtime_amount = 0.0
                            
                            entry_amount = regular_amount + overtime_amount
                            
                            _logger.error(f"  MIDNIGHT period calculation:")
                            _logger.error(f"    Regular hours: {regular_midnight_hours:.2f} × {matching_rule.evening_work_rate_midnight:.2f} = {regular_amount:.2f}")
                            if overtime_hours > 0:
                                _logger.error(f"    Overtime: {overtime_amount:.2f} (First 2: {min(overtime_hours, 2.0):.2f} × {matching_rule.overtime_first_2_hours:.2f}, After 2: {max(0.0, overtime_hours - 2.0):.2f} × {matching_rule.overtime_after_2_hours:.2f})")
                            _logger.error(f"    Total: {entry_amount:.2f}")
                            
                        elif evening_hours > 0 and normal_hours == 0 and evening_midnight_hours == 0:
                            # Work entry is ENTIRELY in evening period (10pm-11:59pm)
                            # Regular hours use evening rate, overtime uses overtime rates
                            regular_evening_hours = min(regular_hours, evening_hours)
                            
                            regular_amount = regular_evening_hours * matching_rule.evening_work_rate
                            
                            # Calculate overtime amount (first 2 hours, then after 2 hours)
                            if overtime_hours > 0:
                                first_2_overtime_hours = min(overtime_hours, 2.0)
                                after_2_overtime_hours = max(0.0, overtime_hours - 2.0)
                                overtime_amount = (first_2_overtime_hours * matching_rule.overtime_first_2_hours) + \
                                                (after_2_overtime_hours * matching_rule.overtime_after_2_hours)
                            else:
                                overtime_amount = 0.0
                            
                            entry_amount = regular_amount + overtime_amount
                            
                            _logger.error(f"  EVENING period calculation:")
                            _logger.error(f"    Regular hours: {regular_evening_hours:.2f} × {matching_rule.evening_work_rate:.2f} = {regular_amount:.2f}")
                            if overtime_hours > 0:
                                _logger.error(f"    Overtime: {overtime_amount:.2f} (First 2: {min(overtime_hours, 2.0):.2f} × {matching_rule.overtime_first_2_hours:.2f}, After 2: {max(0.0, overtime_hours - 2.0):.2f} × {matching_rule.overtime_after_2_hours:.2f})")
                            _logger.error(f"    Total: {entry_amount:.2f}")
                            
                        elif normal_hours > 0 and evening_hours == 0 and evening_midnight_hours == 0:
                            # Work entry is ENTIRELY in normal period (6am-10pm)
                            # Regular hours use hourly rate, overtime uses overtime rates
                            regular_normal_hours = min(regular_hours, normal_hours)
                            
                            regular_amount = regular_normal_hours * normal_rate
                            
                            # Calculate overtime amount (first 2 hours, then after 2 hours)
                            if overtime_hours > 0:
                                first_2_overtime_hours = min(overtime_hours, 2.0)
                                after_2_overtime_hours = max(0.0, overtime_hours - 2.0)
                                overtime_amount = (first_2_overtime_hours * matching_rule.overtime_first_2_hours) + \
                                                (after_2_overtime_hours * matching_rule.overtime_after_2_hours)
                            else:
                                overtime_amount = 0.0
                            
                            entry_amount = regular_amount + overtime_amount
                            
                            _logger.error(f"  NORMAL period calculation:")
                            _logger.error(f"    Regular hours: {regular_normal_hours:.2f} × {normal_rate:.2f} = {regular_amount:.2f}")
                            if overtime_hours > 0:
                                _logger.error(f"    Overtime: {overtime_amount:.2f} (First 2: {min(overtime_hours, 2.0):.2f} × {matching_rule.overtime_first_2_hours:.2f}, After 2: {max(0.0, overtime_hours - 2.0):.2f} × {matching_rule.overtime_after_2_hours:.2f})")
                            _logger.error(f"    Total: {entry_amount:.2f}")
                            
                        else:
                            # Work entry spans multiple time periods
                            # Calculate regular hours proportionally across periods, then apply overtime
                            # Distribute regular hours across time periods proportionally
                            total_regular_hours = min(entry_total_hours, standard_hours_per_day)
                            
                            if entry_total_hours > 0:
                                normal_ratio = normal_hours / entry_total_hours
                                evening_ratio = evening_hours / entry_total_hours
                                midnight_ratio = evening_midnight_hours / entry_total_hours
                                
                                regular_normal = total_regular_hours * normal_ratio
                                regular_evening = total_regular_hours * evening_ratio
                                regular_midnight = total_regular_hours * midnight_ratio
                            else:
                                regular_normal = 0.0
                                regular_evening = 0.0
                                regular_midnight = 0.0
                            
                            # Calculate regular amount using time-based rates
                            normal_amount = regular_normal * normal_rate
                            evening_amount = regular_evening * matching_rule.evening_work_rate
                            evening_midnight_amount = regular_midnight * matching_rule.evening_work_rate_midnight
                            
                            regular_amount = normal_amount + evening_amount + evening_midnight_amount
                            
                            # Calculate overtime amount (first 2 hours, then after 2 hours)
                            if overtime_hours > 0:
                                first_2_overtime_hours = min(overtime_hours, 2.0)
                                after_2_overtime_hours = max(0.0, overtime_hours - 2.0)
                                overtime_amount = (first_2_overtime_hours * matching_rule.overtime_first_2_hours) + \
                                                (after_2_overtime_hours * matching_rule.overtime_after_2_hours)
                            else:
                                overtime_amount = 0.0
                            
                            entry_amount = regular_amount + overtime_amount
                            
                            _logger.error(f"  MULTIPLE periods calculation:")
                            _logger.error(f"    Regular hours breakdown:")
                            _logger.error(f"      Normal: {regular_normal:.2f} × {normal_rate:.2f} = {normal_amount:.2f}")
                            _logger.error(f"      Evening: {regular_evening:.2f} × {matching_rule.evening_work_rate:.2f} = {evening_amount:.2f}")
                            _logger.error(f"      Midnight: {regular_midnight:.2f} × {matching_rule.evening_work_rate_midnight:.2f} = {evening_midnight_amount:.2f}")
                            _logger.error(f"    Regular total: {regular_amount:.2f}")
                            if overtime_hours > 0:
                                _logger.error(f"    Overtime: {overtime_amount:.2f} (First 2: {min(overtime_hours, 2.0):.2f} × {matching_rule.overtime_first_2_hours:.2f}, After 2: {max(0.0, overtime_hours - 2.0):.2f} × {matching_rule.overtime_after_2_hours:.2f})")
                            _logger.error(f"    Total: {entry_amount:.2f}")
                    
                    total_salary += entry_amount
                    total_worked_days += 1.0
                    
                    _logger.error(f"  Work Entry FINAL Amount: {entry_amount:.2f} (Hours: {entry_total_hours:.2f}, "
                                f"Saturday: {is_saturday}, Sunday: {is_sunday})")
                    
                    # Create worked days line
                    # Use local date for the entry date (already calculated above as local_start)
                    entry_date = local_start.date()
                    
                    # Get work entry type
                    work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_attendance', raise_if_not_found=False)
                    if not work_entry_type:
                        work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')], limit=1)
                    
                    # Create worked days line
                    # IMPORTANT: number_of_hours must be a float, not a string
                    # Set amount_manually_set=True to prevent recomputation
                    worked_days_line = self.env['hr.payslip.worked_days'].sudo().create({
                        'payslip_id': payslip.id,
                        'work_entry_type_id': work_entry_type.id if work_entry_type else False,
                        'number_of_days': 1.0,
                        'number_of_hours': entry_total_hours,  # Float value, not string
                        'amount': entry_amount,  # Set the amount directly
                        'amount_manually_set': True,  # Flag to prevent recomputation
                    })
                    
                    _logger.error(f"  Created worked_days line ID {worked_days_line.id} with amount: {entry_amount:.2f}")
                    _logger.error(f"  Verified amount after create: {worked_days_line.amount:.2f}")
                
                # If no work entries, DO NOT create a default worked days line
                # Instead, raise an error or log a warning
                if not work_entries:
                    _logger.error(f"  ERROR: No work entries found for payslip period {payslip.date_from} to {payslip.date_to}")
                    _logger.error(f"  This means the payslip will have NO worked days and NO salary calculation.")
                    _logger.error(f"  Please create work entries for this period before computing the payslip.")
                    # Do NOT create a default worked days line - let the user create work entries first
                    # This prevents incorrect calculations like 38 hours × hourly_rate
                    total_salary = 0.0
                    total_hours = 0.0
                    total_worked_days = 0.0
                    
                    # Still create an empty worked days line to show in the UI, but with 0 hours and 0 amount
                    work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_attendance', raise_if_not_found=False)
                    if not work_entry_type:
                        work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')], limit=1)
                    
                    worked_days_line = self.env['hr.payslip.worked_days'].sudo().create({
                        'payslip_id': payslip.id,
                        'work_entry_type_id': work_entry_type.id if work_entry_type else False,
                        'number_of_days': 0.0,
                        'number_of_hours': 0.0,
                        'amount': 0.0,
                        'amount_manually_set': True,
                    })
                    _logger.error(f"  Created EMPTY worked_days line (0 hours, 0 amount) - work entries must be created first")
                
                # Get salary structure and rules
                structure = payslip.struct_id
                if not structure:
                    # Fall back to standard computation if no structure
                    standard_payslips |= payslip
                    continue
                
                # Get salary rules from the structure
                # We need to find or create salary rules for BASIC and GROSS categories
                basic_category = self.env.ref('hr_payroll.BASIC', raise_if_not_found=False)
                if not basic_category:
                    basic_category = self.env['hr.salary.rule.category'].search([('code', '=', 'BASIC')], limit=1)
                
                gross_category = self.env.ref('hr_payroll.GROSS', raise_if_not_found=False)
                if not gross_category:
                    gross_category = self.env['hr.salary.rule.category'].search([('code', '=', 'GROSS')], limit=1)
                
                # Find existing salary rules in the structure that match our categories
                # If not found, we'll need to create them or use a default rule
                basic_rule = False
                gross_rule = False
                
                if structure.rule_ids:
                    # Try to find BASIC rule
                    basic_rule = structure.rule_ids.filtered(lambda r: r.category_id == basic_category)
                    if basic_rule:
                        basic_rule = basic_rule[0]
                    else:
                        # If no BASIC rule found, try to find any rule with BASIC category
                        basic_rule = self.env['hr.salary.rule'].search([
                            ('struct_id', '=', structure.id),
                            ('category_id', '=', basic_category.id if basic_category else False)
                        ], limit=1)
                    
                    # Try to find GROSS rule
                    gross_rule = structure.rule_ids.filtered(lambda r: r.category_id == gross_category)
                    if gross_rule:
                        gross_rule = gross_rule[0]
                    else:
                        # If no GROSS rule found, try to find any rule with GROSS category
                        gross_rule = self.env['hr.salary.rule'].search([
                            ('struct_id', '=', structure.id),
                            ('category_id', '=', gross_category.id if gross_category else False)
                        ], limit=1)
                
                # If no rules found, create minimal rules or use the first rule from structure
                if not basic_rule and structure.rule_ids:
                    # Use the first rule as a fallback (we'll override the amount anyway)
                    basic_rule = structure.rule_ids[0]
                    _logger.warning(f"No BASIC rule found in structure, using fallback rule: {basic_rule.code}")
                
                if not gross_rule and structure.rule_ids:
                    # Use the first rule as a fallback (we'll override the amount anyway)
                    gross_rule = structure.rule_ids[0]
                    _logger.warning(f"No GROSS rule found in structure, using fallback rule: {gross_rule.code}")
                
                # Create BASIC line - salary_rule_id is REQUIRED, cannot be False
                if basic_category and basic_rule:
                    self.env['hr.payslip.line'].create({
                        'slip_id': payslip.id,
                        'salary_rule_id': basic_rule.id,  # REQUIRED - cannot be False
                        'category_id': basic_category.id,
                        'code': 'BASIC',
                        'name': 'Basic Salary',
                        'quantity': 1.0,
                        'rate': 100.0,
                        'amount': total_salary,
                        'total': total_salary,
                    })
                else:
                    _logger.error(f"Cannot create BASIC line: basic_category={basic_category}, basic_rule={basic_rule}")
                
                # Create GROSS line - salary_rule_id is REQUIRED, cannot be False
                if gross_category and gross_rule:
                    self.env['hr.payslip.line'].create({
                        'slip_id': payslip.id,
                        'salary_rule_id': gross_rule.id,  # REQUIRED - cannot be False
                        'category_id': gross_category.id,
                        'code': 'GROSS',
                        'name': 'Gross Salary',
                        'quantity': 1.0,
                        'rate': 100.0,
                        'amount': total_salary,
                        'total': total_salary,
                    })
                else:
                    _logger.error(f"Cannot create GROSS line: gross_category={gross_category}, gross_rule={gross_rule}")
                
                # Add note with calculation details
                work_entry_details = []
                for work_entry in work_entries:
                    entry_date = work_entry.date_start
                    if isinstance(entry_date, datetime):
                        entry_date = entry_date.date()
                    elif isinstance(entry_date, str):
                        entry_date = fields.Date.from_string(entry_date)
                    
                    normal_h, evening_h, midnight_h, is_sat, is_sun = \
                        self._calculate_hours_by_time_period(work_entry.date_start, work_entry.date_stop)
                    total_h = normal_h + evening_h + midnight_h
                    
                    day_name = "Sunday" if is_sun else ("Saturday" if is_sat else "Weekday")
                    if is_sun:
                        rate_used = matching_rule.sunday_rate
                    elif is_sat:
                        rate_used = matching_rule.saturday_rate
                    else:
                        # For weekdays, use hourly_pay_rate from rule (or fallback)
                        if matching_rule.hourly_pay_rate > 0:
                            rate_used = matching_rule.hourly_pay_rate
                        else:
                            rate_used = matching_rule.weekly_pay_rate / 38.0 if matching_rule.weekly_pay_rate > 0 else 0.0
                    
                    work_entry_details.append(
                        f"Date: {entry_date} ({day_name}), Hours: {total_h:.2f}, Rate: {rate_used:.2f}, Amount: {total_h * rate_used:.2f}"
                    )
                
                # Determine which hourly rate is being used
                if matching_rule.hourly_pay_rate > 0:
                    effective_hourly_rate = matching_rule.hourly_pay_rate
                    rate_source = "hourly_pay_rate (from rule)"
                else:
                    effective_hourly_rate = matching_rule.weekly_pay_rate / 38.0 if matching_rule.weekly_pay_rate > 0 else 0.0
                    rate_source = f"weekly_pay_rate / 38 ({matching_rule.weekly_pay_rate:.2f} / 38)"
                
                note = (
                    f"Custom Computation - Age: {contract.age}, Level: {matching_rule.classification}, "
                    f"Type: {matching_rule.employment_type}\n"
                    f"Rule Rates (from Salary Calculation Rule, NOT from contract wage):\n"
                    f"  - Hourly Pay Rate: {matching_rule.hourly_pay_rate:.2f} ({'USED' if matching_rule.hourly_pay_rate > 0 else 'NOT SET - using fallback'})\n"
                    f"  - Weekly Pay Rate: {matching_rule.weekly_pay_rate:.2f}\n"
                    f"  - Effective Hourly Rate: {effective_hourly_rate:.2f} (from {rate_source})\n"
                    f"  - Saturday Rate: {matching_rule.saturday_rate:.2f}\n"
                    f"  - Sunday Rate: {matching_rule.sunday_rate:.2f}\n"
                    f"  - Evening Rate (10pm-12am): {matching_rule.evening_work_rate:.2f}\n"
                    f"  - Evening Rate (12am-6am): {matching_rule.evening_work_rate_midnight:.2f}\n"
                    f"Work Entries:\n" + "\n".join(work_entry_details) + "\n"
                    f"Total Salary: {total_salary:.2f}\n"
                    f"NOTE: This computation uses rates from Salary Calculation Rule, NOT contract wage/hourly_wage fields."
                )
                payslip.write({'note': note})
                
                _logger.info(f"Payslip {payslip.id} computed: Total Salary = {total_salary:.2f}, "
                            f"Total Hours = {total_hours:.2f}, Total Worked Days = {total_worked_days:.2f}")
                
                # Restore original contract wage after computation
                contract.write({'wage': original_wage})
                if original_hourly_wage is not False and hasattr(contract, 'hourly_wage'):
                    contract.write({'hourly_wage': original_hourly_wage})
                
                _logger.info(f"=== CUSTOM PAYSLIP COMPUTATION COMPLETED for payslip {payslip.id} ===")
            except Exception as e:
                _logger.error(f"ERROR processing custom payslip {payslip.id}: {str(e)}", exc_info=True)
                print(f"ERROR processing custom payslip {payslip.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                # On error, the standard computation (already done) will be used
                # Don't add to standard_payslips as they're already processed
                continue
        
        # Return result (standard_result from standard payslips processing)
        result = standard_result
        
        _logger.error("=== CUSTOM PAYSLIP COMPUTATION METHOD COMPLETED ===")
        print("=== CUSTOM PAYSLIP COMPUTATION METHOD COMPLETED ===")
        return result
    
    @api.model
    def create(self, vals):
        """Override create to automatically compute sheet for computed contracts"""
        payslip = super(HrPayslip, self).create(vals)
        # Don't auto-compute here, let user click the button
        return payslip
    
    def write(self, vals):
        """Override write - if work entries are validated, we might need to recompute"""
        result = super(HrPayslip, self).write(vals)
        return result

