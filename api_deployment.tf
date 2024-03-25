resource "aws_ecs_cluster" "api_cluster" {
  name = "api-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "api_task" {
  family                   = "api-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "api-service"
      image     = "ecr_repository_url/api-service:latest"
      cpu       = 256
      memory    = 512
      essential = true

      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DATABASE_URL"
          value = "database_url"
        },
        {
          name  = "JWT_SECRET_KEY"
          value = "jwt_secret_key"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api_log_group.name
          "awslogs-region"        = "us-west-1"
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api_service" {
  name            = "api-service"
  cluster         = aws_ecs_cluster.api_cluster.id
  task_definition = aws_ecs_task_definition.api_task.arn
  desired_count   = 3
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = ["subnet_id"]
    security_groups  = ["security_group_id"]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_target_group.arn
    container_name   = "api-service"
    container_port   = 80
  }

  depends_on = [aws_ecs_cluster.api_cluster, aws_ecs_task_definition.api_task]
}

resource "aws_cloudwatch_log_group" "api_log_group" {
  name              = "/ecs/api-service"
  retention_in_days = 30
}

resource "aws_lb" "api_load_balancer" {
  name               = "api-load-balancer"
  internal           = false
  load_balancer_type = "application"
  security_groups    = ["load_balancer_security_group_id"]
  subnets            = ["subnet_id"]
}

resource "aws_lb_target_group" "api_target_group" {
  name        = "api-target-group"
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = "vpc_id"

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "api_listener" {
  load_balancer_arn = aws_lb.api_load_balancer.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = "ssl_certificate_arn"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_target_group.arn
  }
}
