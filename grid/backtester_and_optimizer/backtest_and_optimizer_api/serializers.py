from rest_framework import serializers

from backtest_and_optimizer_api.models import Bus, BacktestF1


class BusSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    info = serializers.CharField(required=False)
    num_seats = serializers.IntegerField(required=True)

    def create(self, validated_data):
        return Bus.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.info = validated_data.get("info", instance.info)
        instance.num_seats = validated_data.get("num_seats", instance.num_seats)
        instance.save()
        return instance


class BacktestF1Serializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    chosen_strategy = serializers.CharField(required=True)
    symbol = serializers.CharField(required=True)
    days_of_backtest = serializers.IntegerField(required=True)
    just_backtest = serializers.BooleanField(required=True)
    interval_for_backtest = serializers.FloatField(required=True)
    start_balance = serializers.FloatField(required=True)

    def create(self, validated_data):
        return BacktestF1.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.chosen_strategy = validated_data.get(
            "chosen_strategy", instance.chosen_strategy
        )
        instance.symbol = validated_data.get("symbol", instance.symbol)
        instance.days_of_backtest = validated_data.get(
            "days_of_backtest", instance.days_of_backtest
        )
        instance.just_backtest = validated_data.get(
            "just_backtest", instance.just_backtest
        )
        instance.interval_for_backtest = validated_data.get(
            "interval_for_backtest", instance.interval_for_backtest
        )
        instance.start_balance = validated_data.get(
            "start_balance", instance.start_balance
        )
        instance.save()
        return instance
